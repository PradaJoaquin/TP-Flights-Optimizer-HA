from commons.logger import Logger


class ProcessedMessage:
    def __init__(self, message_id, sent):
        self.message_id = message_id
        self.sent = sent

    def from_str(message_str):
        sent = "S" in message_str
        message_id = int(message_str.split("S")[0])
        return ProcessedMessage(message_id, sent)

    def to_bytes(self, size, byteorder="big"):
        # first byte is 1 if sent, 0 if not sent
        sent_byte = b"\x01" if self.sent else b"\x00"
        message_id_bytes = int(self.message_id).to_bytes(size - 1, byteorder)
        return sent_byte + message_id_bytes

    def from_bytes(bytes, byteorder="big"):
        sent = bytes[0] == True
        message_id = int.from_bytes(bytes[1:], byteorder)
        return ProcessedMessage(message_id, sent)

    def __eq__(self, other):
        return self.message_id == other.message_id and self.sent == other.sent

    def __hash__(self):
        return hash((self.message_id, self.sent))


class LogSearcher:
    def __init__(self, suffix=""):
        self.logger = Logger(suffix)

    def search_for_duplicate_messages(self, client_id, ids_to_search):
        """
        Searches for duplicate messages in the log file.
        """
        messages = self.logger.search_processed(client_id, ids_to_search)
        return [ProcessedMessage.from_str(message) for message in messages]

    def search_for_all_connection_messages(self, client_id):
        """
        Searches for all connection messages in the connection log file.
        """
        return self.logger.obtain_all_connection_messages(client_id)

    def obtain_all_active_connection_clients(self):
        """
        Obtains all the active connection clients from the log file.
        """
        return self.logger.obtain_all_active_connection_clients()

    def search_for_all_duplicate_catcher_messages(self, client_id):
        """
        Searches for all duplicate catcher messages in the duplicate catcher log file.
        """
        return self.logger.obtain_all_duplicate_catcher_messages(client_id)

    def obtain_all_active_duplicate_catcher_clients(self):
        """
        Obtains all the active duplicate catcher clients from the log file.
        """
        return self.logger.obtain_all_active_duplicate_catcher_clients()
