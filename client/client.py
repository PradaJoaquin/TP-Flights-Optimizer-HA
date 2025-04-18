import signal
import logging
import multiprocessing as mp

from protocol_connection import ProtocolConnection, ProtocolConnectionConfig
from file_uploader import FileUploader
from result_handler import ResultHandler
from commons.protocol import MessageProtocolType


class ClientConfig:
    def __init__(
        self,
        server_ip,
        server_port,
        flights_file_path,
        airports_file_path,
        remove_file_header,
        batch_size,
        client_id,
    ):
        self.server_ip = server_ip
        self.server_port = server_port
        self.flights_file_path = flights_file_path
        self.airports_file_path = airports_file_path
        self.remove_file_header = remove_file_header
        self.batch_size = batch_size
        self.client_id = client_id


class Client:
    def __init__(self, config):
        self.config = config

        # maxsize=1 to avoid having too many messages in memory
        send_queue = mp.Queue(maxsize=1)
        results_queue = mp.Queue(maxsize=1)

        protocol_connection_config = ProtocolConnectionConfig(
            self.config.server_ip, self.config.server_port, self.config.client_id
        )

        # Start the process to connect to the server
        self.protocol_connection = mp.Process(
            target=ProtocolConnection(
                protocol_connection_config, send_queue, results_queue
            ).start
        )

        # Start the process to send the airports
        self.airports_sender = mp.Process(
            target=FileUploader(
                MessageProtocolType.AIRPORT,
                self.config.airports_file_path,
                self.config.remove_file_header,
                self.config.batch_size,
                self.config.client_id,
                send_queue,
            ).start
        )

        # Start the process to send the flights
        self.flights_sender = mp.Process(
            target=FileUploader(
                MessageProtocolType.FLIGHT,
                self.config.flights_file_path,
                self.config.remove_file_header,
                self.config.batch_size,
                self.config.client_id,
                send_queue,
            ).start
        )

        # Start the process to receive the results
        self.results_receiver = mp.Process(
            target=ResultHandler(self.config.client_id, results_queue).receive_results
        )

        # Register signal handler for SIGTERM
        signal.signal(signal.SIGTERM, self.__shutdown)
        signal.signal(signal.SIGINT, self.__shutdown)

    def run(self):
        self.protocol_connection.start()
        self.airports_sender.start()
        self.flights_sender.start()
        self.results_receiver.start()

        # Wait for the processes to finish
        self.airports_sender.join()
        logging.info("Airports sender finished")
        self.flights_sender.join()
        logging.info("Waiting for results")
        self.results_receiver.join()

        # Disconnect from the server
        logging.info("Disconnecting from server")
        self.protocol_connection.terminate()
        self.protocol_connection.join()

        logging.info("All processes finished")

    def __shutdown(self, signum=None, frame=None):
        logging.info("Shutting down")
        self.buff.stop()
        if self.airports_sender.exitcode is None:
            self.airports_sender.terminate()
        if self.flights_sender.exitcode is None:
            self.flights_sender.terminate()
        if self.results_receiver.exitcode is None:
            self.results_receiver.terminate()
        logging.info("Shut down completed")
