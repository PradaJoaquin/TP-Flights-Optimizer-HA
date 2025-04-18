import logging
import re

from commons.processor import Processor, Response, ResponseType

STARTING_AIRPORT = "startingAirport"
DESTINATION_AIRPORT = "destinationAirport"
TRAVEL_DURATION = "travelDuration"


class DosMasRapidos(Processor):
    def __init__(self, client_id):
        self.trajectory = {}

    def process(self, message):
        """
        Checks if the travel duration is one of the two fastest and if it is,
        it adds the message to the fastest list
        """
        trajectory = self.convert_message_to_trajectory(message)
        if trajectory not in self.trajectory:
            self.trajectory[trajectory] = [message]
        else:
            self.add_to_fastest(self.trajectory[trajectory], message)

    def add_to_fastest(self, fastest, message):
        """
        Adds the message to the fastest list if the travel duration is one of the two fastest
        """
        travel_duration = self.convert_message_to_travel_duration(message)
        if len(fastest) < 2:
            fastest.append(message)
        else:
            second_fastest = self.convert_message_to_travel_duration(fastest[1])
            print(travel_duration, second_fastest)
            if travel_duration < second_fastest:
                fastest[1] = message
        fastest.sort(key=self.convert_message_to_travel_duration)

    def convert_message_to_trajectory(self, message):
        """
        Converts a message to a trajectory string
        """
        return message[STARTING_AIRPORT] + "-" + message[DESTINATION_AIRPORT]

    def convert_message_to_travel_duration(self, message):
        """
        Converts a message to a travel duration in minutes
        """
        return self.convert_travel_duration(message[TRAVEL_DURATION])

    def convert_travel_duration(self, travel_duration):
        """
        Converts the travel duration from the ISO 8601 duration format to minutes.
        Example:
        PT1H30M -> 90
        P1DT8M -> 1448
        """
        hours = 0
        minutes = 0
        days = 0
        duration_match = re.search(
            r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?", travel_duration
        )
        if duration_match:
            days = int(duration_match.group(1) or 0)
            hours = int(duration_match.group(2) or 0)
            minutes = int(duration_match.group(3) or 0)
        return days * 24 * 60 + hours * 60 + minutes

    def finish_processing(self):
        """
        Returns the fastest messages
        """
        logging.info("Finishing processing")
        messages = []
        for trajectory in self.trajectory:
            for message in self.trajectory[trajectory]:
                messages.append(message)
        return Response(ResponseType.MULTIPLE, messages)
