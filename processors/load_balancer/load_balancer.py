import hashlib
import logging
from commons.processor import Processor, Response, ResponseType


class LoadBalancerConfig:
    def __init__(self, grouper_replicas_count):
        self.grouper_replicas_count = grouper_replicas_count


class LoadBalancer(Processor):
    def __init__(self, config, client_id):
        self.config = config

    def process(self, message):
        """
        Calculates the hash of the message and the queue id to send it to
        """
        route = self.get_route(message)
        message_hash = hashlib.md5(route.encode()).hexdigest()
        queue_id = (int(message_hash, 16) % self.config.grouper_replicas_count) + 1
        return Response(ResponseType.SINGLE, (queue_id, message))

    def get_route(self, message):
        starting_airport = message["startingAirport"]
        destination_airport = message["destinationAirport"]
        return f"{starting_airport}-{destination_airport}"

    def finish_processing(self):
        pass
