from multiprocessing import Process

from commons.health_checker_server import HealthCheckerServer
from grouper import Grouper, GrouperConfig
from commons.log_initializer import initialize_log
from commons.config_initializer import initialize_config
from commons.communication_initializer import CommunicationInitializer
from commons.connection import ConnectionConfig, Connection
from commons.log_guardian import LogGuardian


def main():
    config_inputs = {
        "vuelos_input": str,
        "vuelos_output": str,
        "media_general_input": str,
        "media_general_output": str,
        "logging_level": str,
        "rabbit_host": str,
        "input_type": str,
        "output_type": str,
        "replicas_count": int,
        "replica_id": int,
    }
    config_params = initialize_config(config_inputs)

    logging_level = config_params["logging_level"]
    initialize_log(logging_level)

    # Healthcheck process
    health = Process(target=HealthCheckerServer().run)
    health.start()

    vuelos_log_guardian = LogGuardian("vuelos")

    vuelos_communication_initializer = CommunicationInitializer(
        config_params["rabbit_host"], vuelos_log_guardian
    )
    vuelos_receiver = vuelos_communication_initializer.initialize_receiver(
        config_params["vuelos_input"],
        config_params["input_type"],
        config_params["replica_id"],
        config_params["replicas_count"],
        routing_key=str(config_params["replica_id"]),
        use_duplicate_catcher=True,
    )
    vuelos_sender = vuelos_communication_initializer.initialize_sender(
        config_params["vuelos_output"], config_params["output_type"]
    )

    media_general_log_guardian = LogGuardian("media_general")

    media_general_communication_initializer = CommunicationInitializer(
        config_params["rabbit_host"], media_general_log_guardian
    )

    vuelos_input_fields = ["startingAirport", "destinationAirport", "totalFare"]
    vuelos_output_fields = ["route", "prices"]

    grouper_config = GrouperConfig(
        config_params["replica_id"],
        media_general_log_guardian,
        media_general_communication_initializer,
        config_params["media_general_input"],
        config_params["input_type"],
        config_params["replicas_count"],
        str(config_params["replica_id"]),
        config_params["media_general_output"],
        config_params["output_type"],
    )

    connection_config = ConnectionConfig(
        config_params["replica_id"],
        vuelos_input_fields,
        vuelos_output_fields,
        send_eof=False,
        has_statefull_processor=True,
    )
    Connection(
        connection_config,
        vuelos_receiver,
        vuelos_sender,
        vuelos_log_guardian,
        Grouper,
        grouper_config,
    ).run()

    health.join()


if __name__ == "__main__":
    main()
