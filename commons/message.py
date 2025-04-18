from enum import Enum
from commons.log_searcher import ProcessedMessage
from commons.message_utils import MessageBytesReader, MessageBytesWriter


class MessageType(Enum):
    PROTOCOL = 0
    PROTOCOL_RESULT = 1
    EOF = 2
    EOF_DISCOVERY = 3
    EOF_AGGREGATION = 4
    EOF_FINISH = 5
    EOF_RESULT = 6


class Message:
    def __init__(self, message_type, client_id):
        self.message_type = message_type
        self.client_id = client_id

    def from_bytes(bytes):
        """
        Parse the message and return a Message object
        """
        reader = MessageBytesReader(bytes)

        type = reader.read_int(2)
        client_id = reader.read_int(8)

        if type == MessageType.PROTOCOL.value:
            return ProtocolMessage.from_bytes(client_id, reader)
        elif type == MessageType.PROTOCOL_RESULT.value:
            return ProtocolResultMessage.from_bytes(client_id, reader)
        elif type == MessageType.EOF.value:
            return EOFMessage.from_bytes(client_id, reader)
        elif type == MessageType.EOF_DISCOVERY.value:
            return EOFDiscoveryMessage.from_bytes(client_id, reader)
        elif type == MessageType.EOF_AGGREGATION.value:
            return EOFAggregationMessage.from_bytes(client_id, reader)
        elif type == MessageType.EOF_FINISH.value:
            return EOFFinishMessage.from_bytes(client_id, reader)
        elif type == MessageType.EOF_RESULT.value:
            return EOFResultMessage.from_bytes(client_id, reader)
        else:
            raise Exception("Unknown message type")

    def to_bytes(self):
        writer = MessageBytesWriter()

        writer.write_int(self.message_type.value, 2)
        writer.write_int(self.client_id, 8)

        return self.to_bytes_impl(writer)

    def to_bytes_impl(self, writer):
        raise NotImplementedError(
            "to_bytes_impl not implemented, subclass must implement it"
        )


class ProtocolMessage(Message):
    """
    Protocol message structure:

        0      2          10           18         N
        | type | client_id | message_id | payload |

    """

    def __init__(self, client_id, message_id, payload):
        message_type = MessageType.PROTOCOL
        super().__init__(message_type, client_id)
        self.message_id = message_id
        self.payload = payload

    def from_bytes(client_id, reader):
        message_id = reader.read_int(8)
        payload = reader.read_to_end()
        payload = payload.decode("utf-8")

        return ProtocolMessage(client_id, message_id, payload)

    def to_bytes_impl(self, writer):
        writer.write_int(self.message_id, 8)
        writer.write(self.payload.encode("utf-8"))
        return writer.get_bytes()


class ProtocolResultMessage(Message):
    """
    Protocol message structure:

        0      2          10       11           19         N
        | type | client_id | tag_id | message_id | payload |

    """

    def __init__(self, client_id, tag_id, message_id, payload):
        message_type = MessageType.PROTOCOL_RESULT
        super().__init__(message_type, client_id)
        self.tag_id = tag_id
        self.message_id = message_id
        self.payload = payload

    def from_bytes(client_id, reader):
        tag_id = reader.read_int(1)
        message_id = reader.read_int(8)
        payload = reader.read_to_end()
        payload = payload.decode("utf-8")

        return ProtocolResultMessage(client_id, tag_id, message_id, payload)

    def to_bytes_impl(self, writer):
        writer.write_int(self.tag_id, 1)
        writer.write_int(self.message_id, 8)
        writer.write(self.payload.encode("utf-8"))
        return writer.get_bytes()


class EOFMessage(Message):
    """
    EOF message structure:

        0      2          10               18                         22                     N
        | type | client_id | messages_sent | possible_duplicates_count | possible_duplicates |

        A possible duplicate is the id of a message that was sent to the client but the client

    """

    def __init__(self, client_id, messages_sent, possible_duplicates=[]):
        message_type = MessageType.EOF
        super().__init__(message_type, client_id)
        self.messages_sent = messages_sent
        self.possible_duplicates = possible_duplicates

    def from_bytes(client_id, reader):
        messages_sent = reader.read_int(8)
        possible_duplicates_count = reader.read_int(4)
        possible_duplicates = reader.read_multiple_int(8, possible_duplicates_count)

        return EOFMessage(client_id, messages_sent, possible_duplicates)

    def to_bytes_impl(self, writer):
        writer.write_int(self.messages_sent, 8)

        writer.write_int(len(self.possible_duplicates), 4)
        writer.write_multiple_int(self.possible_duplicates, 8)

        return writer.get_bytes()


class EOFDiscoveryMessage(Message):
    """
    EOF discovery message structure:

        0      2          10                       18                                   22                              N
        | type | client_id | original_messages_sent | original_possible_duplicates_count | original_possible_duplicates |

        N                  N+8             N+16                        N+24                   X
        | messages_received | messages_sent | possible_duplicates_count | possible_duplicates |

        X                      X+4                Y
        | replica_id_seen_count | replica_id_seen |
    """

    def __init__(
        self,
        client_id,
        original_messages_sent,
        original_possible_duplicates,
        messages_received,
        messages_sent,
        possible_duplicates,
        replica_id_seen,
    ):
        message_type = MessageType.EOF_DISCOVERY
        super().__init__(message_type, client_id)
        self.original_messages_sent = original_messages_sent

        self.original_possible_duplicates = original_possible_duplicates

        self.messages_received = messages_received
        self.messages_sent = messages_sent

        self.possible_duplicates = possible_duplicates

        self.replica_id_seen = replica_id_seen

    def from_bytes(client_id, reader):
        original_messages_sent = reader.read_int(8)

        original_possible_duplicates_count = reader.read_int(4)
        original_possible_duplicates = reader.read_multiple_int(
            8, original_possible_duplicates_count
        )

        messages_received = reader.read_int(8)
        messages_sent = reader.read_int(8)

        possible_duplicates_count = reader.read_int(4)
        possible_duplicates = reader.read_multiple_int(8, possible_duplicates_count)

        replica_id_seen_count = reader.read_int(4)
        replica_id_seen = reader.read_multiple_int(8, replica_id_seen_count)

        return EOFDiscoveryMessage(
            client_id,
            original_messages_sent,
            original_possible_duplicates,
            messages_received,
            messages_sent,
            possible_duplicates,
            replica_id_seen,
        )

    def to_bytes_impl(self, writer):
        writer.write_int(self.original_messages_sent, 8)

        writer.write_int(len(self.original_possible_duplicates), 4)
        writer.write_multiple_int(self.original_possible_duplicates, 8)

        writer.write_int(self.messages_received, 8)
        writer.write_int(self.messages_sent, 8)

        writer.write_int(len(self.possible_duplicates), 4)
        writer.write_multiple_int(self.possible_duplicates, 8)

        writer.write_int(len(self.replica_id_seen), 4)
        writer.write_multiple_int(self.replica_id_seen, 8)

        return writer.get_bytes()


class EOFAggregationMessage(Message):
    """
    EOF aggregation message structure:

        0      2          10                       18                                   22                              N
        | type | client_id | original_messages_sent | original_possible_duplicates_count | original_possible_duplicates |

        N                  N+8             N+16                        N+20                   X
        | messages_received | messages_sent | possible_duplicates_count | possible_duplicates |

        X                      X+4                Y                                      Y+4                                Z
        | replica_id_seen_count | replica_id_seen | possible_duplicates_processed_by_count | possible_duplicates_processed_by |

    """

    # TODO: It is practically the same as EOFDiscoveryMessage, only with processed_by parameter, we should merge them.

    def __init__(
        self,
        client_id,
        original_messages_sent,
        original_possible_duplicates,
        messages_received,
        messages_sent,
        possible_duplicates,
        replica_id_seen,
        possible_duplicates_processed_by,
    ):
        message_type = MessageType.EOF_AGGREGATION
        super().__init__(message_type, client_id)
        self.original_messages_sent = original_messages_sent

        self.original_possible_duplicates = original_possible_duplicates

        self.messages_received = messages_received
        self.messages_sent = messages_sent

        self.possible_duplicates = possible_duplicates

        self.replica_id_seen = replica_id_seen

        self.possible_duplicates_processed_by = possible_duplicates_processed_by

    def from_bytes(client_id, reader):
        original_messages_sent = reader.read_int(8)

        original_possible_duplicates_count = reader.read_int(4)
        original_possible_duplicates = reader.read_multiple_int(
            8, original_possible_duplicates_count
        )

        messages_received = reader.read_int(8)
        messages_sent = reader.read_int(8)

        possible_duplicates_count = reader.read_int(4)
        possible_duplicates = reader.read_multiple_int(8, possible_duplicates_count)

        replica_id_seen_count = reader.read_int(4)
        replica_id_seen = reader.read_multiple_int(8, replica_id_seen_count)

        possible_duplicates_processed_by_count = reader.read_int(4)
        possible_duplicates_processed_by = reader.read_multiple_object(
            9, possible_duplicates_processed_by_count, ProcessedMessage
        )

        return EOFAggregationMessage(
            client_id,
            original_messages_sent,
            original_possible_duplicates,
            messages_received,
            messages_sent,
            possible_duplicates,
            replica_id_seen,
            possible_duplicates_processed_by,
        )

    def to_bytes_impl(self, writer):
        writer.write_int(self.original_messages_sent, 8)

        writer.write_int(len(self.original_possible_duplicates), 4)
        writer.write_multiple_int(self.original_possible_duplicates, 8)

        writer.write_int(self.messages_received, 8)
        writer.write_int(self.messages_sent, 8)

        writer.write_int(len(self.possible_duplicates), 4)
        writer.write_multiple_int(self.possible_duplicates, 8)

        writer.write_int(len(self.replica_id_seen), 4)
        writer.write_multiple_int(self.replica_id_seen, 8)

        writer.write_int(len(self.possible_duplicates_processed_by), 4)
        writer.write_multiple_int(self.possible_duplicates_processed_by, 9)

        return writer.get_bytes()


class EOFFinishMessage(Message):
    """
    EOF finish message structure:

        0      2           10                     14                 N
        | type | client_id | replica_id_seen_count | replica_id_seen |

    """

    def __init__(self, client_id, replica_id_seen):
        message_type = MessageType.EOF_FINISH
        super().__init__(message_type, client_id)
        self.replica_id_seen = replica_id_seen

    def from_bytes(client_id, reader):
        replica_id_seen_count = reader.read_int(4)
        replica_id_seen = reader.read_multiple_int(8, replica_id_seen_count)

        return EOFFinishMessage(client_id, replica_id_seen)

    def to_bytes_impl(self, writer):
        writer.write_int(len(self.replica_id_seen), 4)
        writer.write_multiple_int(self.replica_id_seen, 8)

        return writer.get_bytes()


class EOFResultMessage(Message):
    """
    EOF result message structure:

        0      2          10       11              19
        | type | client_id | tag_id | messages_sent |

    """

    def __init__(self, client_id, tag_id, messages_sent):
        message_type = MessageType.EOF_RESULT
        super().__init__(message_type, client_id)
        self.tag_id = tag_id
        self.messages_sent = messages_sent

    def from_bytes(client_id, reader):
        tag_id = reader.read_int(1)
        messages_sent = reader.read_int(8)

        return EOFResultMessage(client_id, tag_id, messages_sent)

    def to_bytes_impl(self, writer):
        writer.write_int(self.tag_id, 1)
        writer.write_int(self.messages_sent, 8)

        return writer.get_bytes()
