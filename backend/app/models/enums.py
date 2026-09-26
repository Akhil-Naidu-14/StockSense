from enum import Enum


class UserRole(str, Enum):
    INVENTORY_MANAGER = "INVENTORY_MANAGER"
    WAREHOUSE_STAFF = "WAREHOUSE_STAFF"


class ReceiptStatus(str, Enum):
    DRAFT = "DRAFT"
    WAITING = "WAITING"
    RECEIVED = "RECEIVED"
    CANCELED = "CANCELED"


class DeliveryStatus(str, Enum):
    DRAFT = "DRAFT"
    WAITING = "WAITING"
    READY = "READY"
    PICKED = "PICKED"
    PACKED = "PACKED"
    DONE = "DONE"
    CANCELED = "CANCELED"


class TransferStatus(str, Enum):
    DRAFT = "DRAFT"
    WAITING = "WAITING"
    IN_TRANSIT = "IN_TRANSIT"
    DONE = "DONE"
    CANCELED = "CANCELED"


class AdjustmentStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DONE = "DONE"
    CANCELED = "CANCELED"


class LedgerTransactionType(str, Enum):
    INITIAL_STOCK = "INITIAL_STOCK"
    RECEIPT = "RECEIPT"
    DELIVERY = "DELIVERY"
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"
