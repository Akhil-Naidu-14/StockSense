from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.models import Location, Product, ReorderRule
from app.schemas.reorder_rule import (
    ReorderRuleCreate,
    ReorderRuleResponse,
    ReorderRuleUpdate,
)


class ReorderService:

    @classmethod
    def build_reorder_response(cls, rule: ReorderRule) -> ReorderRuleResponse:
        prod_name = rule.product.name if rule.product else None
        sku = rule.product.sku if rule.product else None

        loc_name = rule.location.name if rule.location else None
        wh_id = rule.location.warehouse_id if rule.location else None
        wh_name = rule.location.warehouse.name if rule.location and rule.location.warehouse else None

        return ReorderRuleResponse(
            id=rule.id,
            product_id=rule.product_id,
            product_name=prod_name,
            sku=sku,
            location_id=rule.location_id,
            location_name=loc_name,
            warehouse_id=wh_id,
            warehouse_name=wh_name,
            minimum_quantity=rule.minimum_quantity,
            reorder_quantity=rule.reorder_quantity,
            active=rule.active,
        )

    @classmethod
    def create_reorder_rule(
        cls, db: Session, payload: ReorderRuleCreate
    ) -> ReorderRuleResponse:
        # Validate product
        product = db.query(Product).filter(Product.id == payload.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {payload.product_id} not found",
            )
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with ID {payload.product_id} is inactive",
            )

        # Validate location if provided
        if payload.location_id is not None:
            location = db.query(Location).filter(Location.id == payload.location_id).first()
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Location with ID {payload.location_id} not found",
                )
            if not location.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Location with ID {payload.location_id} is inactive",
                )

        # Prevent duplicate active rules for same scope
        if payload.active:
            query = db.query(ReorderRule).filter(
                ReorderRule.product_id == payload.product_id,
                ReorderRule.active.is_(True),
            )
            if payload.location_id is not None:
                query = query.filter(ReorderRule.location_id == payload.location_id)
            else:
                query = query.filter(ReorderRule.location_id.is_(None))

            existing = query.first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An active reorder rule already exists for this product and location scope.",
                )

        rule = ReorderRule(
            product_id=payload.product_id,
            location_id=payload.location_id,
            minimum_quantity=payload.minimum_quantity,
            reorder_quantity=payload.reorder_quantity,
            active=payload.active if payload.active is not None else True,
        )

        try:
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return cls.build_reorder_response(rule)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create reorder rule.",
            )

    @classmethod
    def get_reorder_rule(cls, db: Session, rule_id: int) -> ReorderRuleResponse:
        rule = db.query(ReorderRule).filter(ReorderRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reorder rule with ID {rule_id} not found",
            )
        return cls.build_reorder_response(rule)

    @classmethod
    def list_reorder_rules(
        cls,
        db: Session,
        product_id: Optional[int] = None,
        location_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        active_only: Optional[bool] = None,
    ) -> List[ReorderRuleResponse]:
        query = db.query(ReorderRule)

        if product_id is not None:
            query = query.filter(ReorderRule.product_id == product_id)

        if location_id is not None:
            query = query.filter(ReorderRule.location_id == location_id)

        if warehouse_id is not None:
            query = query.join(Location, ReorderRule.location_id == Location.id).filter(
                Location.warehouse_id == warehouse_id
            )

        if active_only is not None and active_only:
            query = query.filter(ReorderRule.active.is_(True))

        rules = query.order_by(ReorderRule.id.desc()).all()
        return [cls.build_reorder_response(r) for r in rules]

    @classmethod
    def update_reorder_rule(
        cls, db: Session, rule_id: int, payload: ReorderRuleUpdate
    ) -> ReorderRuleResponse:
        rule = db.query(ReorderRule).filter(ReorderRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reorder rule with ID {rule_id} not found",
            )

        target_product_id = payload.product_id if payload.product_id is not None else rule.product_id
        target_location_id = payload.location_id if payload.location_id is not None else rule.location_id
        target_active = payload.active if payload.active is not None else rule.active

        if payload.product_id is not None and payload.product_id != rule.product_id:
            product = db.query(Product).filter(Product.id == payload.product_id).first()
            if not product or not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product with ID {payload.product_id} is inactive or missing",
                )
            rule.product_id = payload.product_id

        if payload.location_id is not None and payload.location_id != rule.location_id:
            location = db.query(Location).filter(Location.id == payload.location_id).first()
            if not location or not location.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Location with ID {payload.location_id} is inactive or missing",
                )
            rule.location_id = payload.location_id

        if payload.minimum_quantity is not None:
            rule.minimum_quantity = payload.minimum_quantity

        if payload.reorder_quantity is not None:
            rule.reorder_quantity = payload.reorder_quantity

        if payload.active is not None:
            rule.active = payload.active

        if target_active:
            query = db.query(ReorderRule).filter(
                ReorderRule.product_id == target_product_id,
                ReorderRule.active.is_(True),
                ReorderRule.id != rule_id,
            )
            if target_location_id is not None:
                query = query.filter(ReorderRule.location_id == target_location_id)
            else:
                query = query.filter(ReorderRule.location_id.is_(None))

            existing = query.first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An active reorder rule already exists for this product and location scope.",
                )

        try:
            db.commit()
            db.refresh(rule)
            return cls.build_reorder_response(rule)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update reorder rule.",
            )

    @classmethod
    def delete_reorder_rule(cls, db: Session, rule_id: int) -> ReorderRuleResponse:
        rule = db.query(ReorderRule).filter(ReorderRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reorder rule with ID {rule_id} not found",
            )

        try:
            rule.active = False
            db.commit()
            db.refresh(rule)
            return cls.build_reorder_response(rule)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to deactivate reorder rule.",
            )
