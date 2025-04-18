import logging
import signal
import socket
import multiprocessing as mp
from enum import Enum

from commons.communication_buffer import CommunicationBuffer
from commons.protocol import AnnounceMessage, MessageType, ResultACKMessage


class ProtocolConnectionConfig:
    def __init__(self, server_ip, server_port, client_id):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_id = client_id


class ProtocolConnection:
    def __init__(self, config, send_queue, results_queue):
        self.config = config
        self.sending_messages = True
        self.waiting_results = True
        self.send_queue = send_queue
        self.results_queue = results_queue
        self.ack_queue = mp.Queue()
        self.current_message = None
        self.eofs_received = 0
        self.possible_duplicates = []

    def start(self):
        """
        Starts the protocol connection.
        """
        # Register signal handler for SIGTERM
        signal.signal(signal.SIGTERM, self.__shutdown)
        signal.signal(signal.SIGINT, self.__shutdown)

        self.__reconnect()

    def __reconnect(self):
        """
        Reconnects to the server.
        """
        if not self.waiting_results and not self.sending_messages:
            # If we are not waiting for results and we are not sending messages, we don't need to reconnect
            return

        connected = False
        while not connected:
            try:
                logging.debug("Connecting to server...")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.config.server_ip, self.config.server_port))
                self.buff = CommunicationBuffer(self.sock)
                self.__send_announce()
                connected = True
            except Exception as e:
                logging.error(f"Error connecting to server: {e}")
        logging.debug("Connected to server")
        self.receiver_proc = mp.Process(
            target=Receiver(
                self.buff, self.send_queue, self.results_queue, self.ack_queue
            ).run
        )
        # Clear the ack queue to avoid receiving old messages
        while not self.ack_queue.empty():
            self.ack_queue.get()

        self.receiver_proc.start()
        self.__run()

    def __send_announce(self):
        """
        Sends the announce message to the server.
        """
        logging.debug("Sending announce...")
        announce_message = AnnounceMessage(self.config.client_id)
        self.buff.send_message(announce_message)
        recv_message = self.buff.get_message()
        while recv_message.message_type != MessageType.ANNOUNCE_ACK:
            logging.debug(f"Received message: {recv_message} | Retrying announce...")
            self.buff.send_message(announce_message)
            recv_message = self.buff.get_message()

    def __run(self):
        """
        Runs the protocol connection.
        """
        while self.sending_messages:
            if not self.current_message:
                self.current_message = self.send_queue.get()
            else:
                logging.debug(
                    f"Current message found: {self.current_message}. Resending..."
                )
                logging.debug(
                    f"Adding message {self.current_message.message_id} to possible duplicates"
                )
                self.possible_duplicates.append(self.current_message.message_id)
            if self.current_message.message_type == MessageType.EOF:
                self.current_message.possible_duplicates = self.possible_duplicates
            self.__send(self.current_message)
            if self.eofs_received == 2:
                logging.debug("All EOFs sent.")
                self.sending_messages = False
        while self.waiting_results:
            logging.debug("Waiting for results...")
            # This is done to be able to reconnect in case of server crash
            try:
                self.__receive_ack()
            except Exception as e:
                self.__reconnect()

    def __send(self, message):
        """
        Sends a message to the client.
        """
        logging.info(f"Sending message: {message}")
        try:
            self.buff.send_message(message)
            self.__receive_ack()
        except Exception as e:
            logging.error("Error while sending a message to server in the Sender")
            self.__reconnect()

    def __receive_ack(self):
        connection_state, recv_message = self.ack_queue.get()
        if connection_state == ConnectionState.DISCONNECTED:
            logging.error("Received a disconnection message from the receiver")
            raise Exception("Server disconnected")
        if recv_message.message_type == MessageType.ACK:
            if self.current_message.message_type == MessageType.EOF:
                self.eofs_received += 1
            self.current_message = None

    def __shutdown(self, *args):
        """
        Graceful shutdown. Closing all connections.
        """
        logging.info("action: ProtocolConnection shutdown | result: in_progress")
        self.sending_messages = False
        self.waiting_results = False
        self.receiver_proc.terminate()
        logging.info("action: ProtocolConnection shutdown | result: success")


class Receiver:
    def __init__(self, buff, send_queue, results_queue, ack_queue):
        self.buff = buff
        self.send_queue = send_queue
        self.results_queue = results_queue
        self.ack_queue = ack_queue
        self.running = True

    def run(self):
        """
        Receives messages from the server.
        """
        # Register signal handler for SIGTERM
        signal.signal(signal.SIGTERM, self.__shutdown)
        signal.signal(signal.SIGINT, self.__shutdown)

        while self.running:
            try:
                message = self.buff.get_message()
                if (
                    message.message_type == MessageType.RESULT
                    or message.message_type == MessageType.RESULT_EOF
                ):
                    if message.message_type == MessageType.RESULT:
                        logging.debug(
                            f"Received Result: {message.message_id}, {message.tag_id}"
                        )
                    self.results_queue.put(message)
                    self.buff.send_message(ResultACKMessage())
                else:
                    logging.debug(f"Received ACK: {message.message_id}")
                    self.ack_queue.put((ConnectionState.CONNECTED, message))
            except Exception as e:
                logging.error(f"Error while receiving message from Receiver: {e}")
                self.running = False
                self.ack_queue.put((ConnectionState.DISCONNECTED, None))

    def __shutdown(self, *args):
        """
        Graceful shutdown. Closing all connections.
        """
        logging.info("action: Receiver shutdown | result: in_progress")
        self.buff.stop()
        logging.info("action: Receiver shutdown | result: success")


class ConnectionState(Enum):
    CONNECTED = 0
    DISCONNECTED = 1
