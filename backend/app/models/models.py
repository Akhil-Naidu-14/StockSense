from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import (
    AdjustmentStatus,
    DeliveryStatus,
    LedgerTransactionType,
    ReceiptStatus,
    TransferStatus,
    UserRole,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), default=UserRole.WAREHOUSE_STAFF, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    reset_otps: Mapped[List["PasswordResetOTP"]] = relationship(
        "PasswordResetOTP", back_populates="user", cascade="all, delete-orphan"
    )
    managed_warehouses: Mapped[List["Warehouse"]] = relationship("Warehouse", back_populates="manager")
    created_receipts: Mapped[List["Receipt"]] = relationship("Receipt", back_populates="creator")
    created_deliveries: Mapped[List["Delivery"]] = relationship("Delivery", back_populates="creator")
    created_transfers: Mapped[List["Transfer"]] = relationship("Transfer", back_populates="creator")
    created_adjustments: Mapped[List["Adjustment"]] = relationship("Adjustment", back_populates="creator")
    performed_ledger_entries: Mapped[List["StockLedger"]] = relationship(
        "StockLedger", back_populates="performer"
    )


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    otp: Mapped[str] = mapped_column(String(10), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reset_otps")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unit_of_measure: Mapped[str] = mapped_column(String(50), nullable=False, default="pcs")
    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0.0000"), nullable=False
    )
    reorder_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0.0000"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products")
    inventories: Mapped[List["Inventory"]] = relationship(
        "Inventory", back_populates="product", cascade="all, delete-orphan"
    )
    receipt_items: Mapped[List["ReceiptItem"]] = relationship("ReceiptItem", back_populates="product")
    delivery_items: Mapped[List["DeliveryItem"]] = relationship("DeliveryItem", back_populates="product")
    transfer_items: Mapped[List["TransferItem"]] = relationship("TransferItem", back_populates="product")
    adjustments: Mapped[List["Adjustment"]] = relationship("Adjustment", back_populates="product")
    reorder_rules: Mapped[List["ReorderRule"]] = relationship(
        "ReorderRule", back_populates="product", cascade="all, delete-orphan"
    )
    ledger_entries: Mapped[List["StockLedger"]] = relationship("StockLedger", back_populates="product")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    manager: Mapped[Optional["User"]] = relationship("User", back_populates="managed_warehouses")
    locations: Mapped[List["Location"]] = relationship(
        "Location", back_populates="warehouse", cascade="all, delete-orphan"
    )


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    warehouse_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    location_type: Mapped[str] = mapped_column(String(50), nullable=False, default="internal")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="locations")
    inventories: Mapped[List["Inventory"]] = relationship(
        "Inventory", back_populates="location", cascade="all, delete-orphan"
    )
    receipts: Mapped[List["Receipt"]] = relationship("Receipt", back_populates="location")
    deliveries: Mapped[List["Delivery"]] = relationship("Delivery", back_populates="location")
    source_transfers: Mapped[List["Transfer"]] = relationship(
        "Transfer", foreign_keys="[Transfer.source_location_id]", back_populates="source_location"
    )
    destination_transfers: Mapped[List["Transfer"]] = relationship(
        "Transfer", foreign_keys="[Transfer.destination_location_id]", back_populates="destination_location"
    )
    adjustments: Mapped[List["Adjustment"]] = relationship("Adjustment", back_populates="location")
    reorder_rules: Mapped[List["ReorderRule"]] = relationship("ReorderRule", back_populates="location")
    source_ledger_entries: Mapped[List["StockLedger"]] = relationship(
        "StockLedger", foreign_keys="[StockLedger.source_location_id]", back_populates="source_location"
    )
    destination_ledger_entries: Mapped[List["StockLedger"]] = relationship(
        "StockLedger", foreign_keys="[StockLedger.destination_location_id]", back_populates="destination_location"
    )


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0.0000"), nullable=False
    )
    reserved_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0.0000"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("product_id", "location_id", name="uq_inventory_product_location"),
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="inventories")
    location: Mapped["Location"] = relationship("Location", back_populates="inventories")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    supplier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[ReceiptStatus] = mapped_column(
        Enum(ReceiptStatus, native_enum=False), default=ReceiptStatus.DRAFT, nullable=False
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    location: Mapped["Location"] = relationship("Location", back_populates="receipts")
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="created_receipts")
    items: Mapped[List["ReceiptItem"]] = relationship(
        "ReceiptItem", back_populates="receipt", cascade="all, delete-orphan"
    )


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0.0000"), nullable=False
    )

    # Relationships
    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="receipt_items")


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    customer_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, native_enum=False), default=DeliveryStatus.DRAFT, nullable=False
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    location: Mapped["Location"] = relationship("Location", back_populates="deliveries")
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="created_deliveries")
    items: Mapped[List["DeliveryItem"]] = relationship(
        "DeliveryItem", back_populates="delivery", cascade="all, delete-orphan"
    )


class DeliveryItem(Base):
    __tablename__ = "delivery_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    # Relationships
    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="delivery_items")


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transfer_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    source_location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    destination_location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, native_enum=False), default=TransferStatus.DRAFT, nullable=False
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships with explicit foreign_keys to resolve ambiguity
    source_location: Mapped["Location"] = relationship(
        "Location", foreign_keys=[source_location_id], back_populates="source_transfers"
    )
    destination_location: Mapped["Location"] = relationship(
        "Location", foreign_keys=[destination_location_id], back_populates="destination_transfers"
    )
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="created_transfers")
    items: Mapped[List["TransferItem"]] = relationship(
        "TransferItem", back_populates="transfer", cascade="all, delete-orphan"
    )


class TransferItem(Base):
    __tablename__ = "transfer_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transfer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transfers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    # Relationships
    transfer: Mapped["Transfer"] = relationship("Transfer", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="transfer_items")


class Adjustment(Base):
    __tablename__ = "adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    system_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    counted_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[AdjustmentStatus] = mapped_column(
        Enum(AdjustmentStatus, native_enum=False), default=AdjustmentStatus.DRAFT, nullable=False
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="adjustments")
    location: Mapped["Location"] = relationship("Location", back_populates="adjustments")
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="created_adjustments")


class ReorderRule(Base):
    __tablename__ = "reorder_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    minimum_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    reorder_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="reorder_rules")
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="reorder_rules")


class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_type: Mapped[LedgerTransactionType] = mapped_column(
        Enum(LedgerTransactionType, native_enum=False), nullable=False, index=True
    )
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    destination_location_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quantity_before: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    quantity_after: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships with explicit foreign_keys
    product: Mapped["Product"] = relationship("Product", back_populates="ledger_entries")
    source_location: Mapped[Optional["Location"]] = relationship(
        "Location", foreign_keys=[source_location_id], back_populates="source_ledger_entries"
    )
    destination_location: Mapped[Optional["Location"]] = relationship(
        "Location", foreign_keys=[destination_location_id], back_populates="destination_ledger_entries"
    )
    performer: Mapped[Optional["User"]] = relationship(
        "User", back_populates="performed_ledger_entries"
    )
