from datetime import datetime
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_any_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import (
    InventoryAgingItem,
    MovementAnalysisItem,
    StockValuationItem,
)
from app.schemas.inventory_reports import (
    InventoryExecutiveDashboardResponse,
    InventoryMovementAnalyticsResponse,
    PaginatedAvailableStockReportResponse,
    PaginatedBatchExpiryReportResponse,
    PaginatedInventoryAgingReportResponse,
    PaginatedLowStockReportResponse,
    PaginatedProductInventoryReportResponse,
    PaginatedSerialInventoryReportResponse,
    PaginatedStockMovementReportResponse,
    PaginatedStockReportResponse,
    PaginatedStockReservationReportResponse,
    PaginatedWarehouseInventoryReportResponse,
)
from app.services.inventory_report_services import inventory_report_service

router = APIRouter()


# =============================================================================
# 1. CURRENT STOCK REPORT & EXPORT
# =============================================================================
@router.get(
    "/stock",
    response_model=PaginatedStockReportResponse,
    dependencies=[Depends(has_any_permission("inventory.report.stock.read", "inventory.reports.read"))],
)
async def get_current_stock_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    tracking_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Authoritative Current Stock & Balance Report."""
    return await inventory_report_service.get_current_stock_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        category_id=category_id,
        tracking_type=tracking_type,
        active_only=active_only,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/stock/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_current_stock_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    tracking_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Current Stock Report to CSV."""
    report = await inventory_report_service.get_current_stock_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        category_id=category_id,
        tracking_type=tracking_type,
        active_only=active_only,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("stock", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_report.csv"},
    )


# =============================================================================
# 2. STOCK MOVEMENT REPORT & EXPORT
# =============================================================================
@router.get(
    "/movements",
    response_model=PaginatedStockMovementReportResponse,
    dependencies=[Depends(has_any_permission("inventory.report.movement.read", "inventory.reports.read"))],
)
async def get_stock_movement_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    movement_type: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    batch_id: Optional[uuid.UUID] = Query(None),
    reference_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Authoritative Historical Stock Movement Ledger Report."""
    return await inventory_report_service.get_stock_movement_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        movement_type=movement_type,
        direction=direction,
        batch_id=batch_id,
        reference_type=reference_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/movements/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_stock_movement_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    movement_type: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    batch_id: Optional[uuid.UUID] = Query(None),
    reference_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Stock Movements to CSV."""
    report = await inventory_report_service.get_stock_movement_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        movement_type=movement_type,
        direction=direction,
        batch_id=batch_id,
        reference_type=reference_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("movements", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_movements_report.csv"},
    )


# =============================================================================
# 3. WAREHOUSE INVENTORY REPORT & EXPORT
# =============================================================================
@router.get(
    "/warehouses",
    response_model=PaginatedWarehouseInventoryReportResponse,
    dependencies=[Depends(has_any_permission("inventory.report.warehouse.read", "inventory.reports.read"))],
)
async def get_warehouse_inventory_report(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Warehouse-Level Inventory Aggregation Report."""
    return await inventory_report_service.get_warehouse_inventory_report(
        db=db,
        warehouse_id=warehouse_id,
        is_active=is_active,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/warehouses/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_warehouse_inventory_report(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Warehouse Inventory Report to CSV."""
    report = await inventory_report_service.get_warehouse_inventory_report(
        db=db,
        warehouse_id=warehouse_id,
        is_active=is_active,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("warehouses", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=warehouse_inventory_report.csv"},
    )


# =============================================================================
# 4. PRODUCT INVENTORY REPORT & EXPORT
# =============================================================================
@router.get(
    "/products",
    response_model=PaginatedProductInventoryReportResponse,
    dependencies=[Depends(has_any_permission("inventory.report.product.read", "inventory.reports.read"))],
)
async def get_product_inventory_report(
    product_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    tracking_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Product-Level Multi-Location Inventory Report."""
    return await inventory_report_service.get_product_inventory_report(
        db=db,
        product_id=product_id,
        category_id=category_id,
        tracking_type=tracking_type,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/products/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_product_inventory_report(
    product_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    tracking_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Product Inventory Report to CSV."""
    report = await inventory_report_service.get_product_inventory_report(
        db=db,
        product_id=product_id,
        category_id=category_id,
        tracking_type=tracking_type,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("products", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=product_inventory_report.csv"},
    )


# =============================================================================
# 5. BATCH & EXPIRY REPORT & EXPORT
# =============================================================================
@router.get(
    "/batches/expiry",
    response_model=PaginatedBatchExpiryReportResponse,
    dependencies=[Depends(has_any_permission("inventory.report.batch.read", "inventory.reports.read"))],
)
async def get_batch_expiry_report(
    product_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    expiry_status: Optional[str] = Query(None),
    expiring_within_days: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Batch Status, Shelf-Life & Expiry Countdown Report."""
    return await inventory_report_service.get_batch_expiry_report(
        db=db,
        product_id=product_id,
        status=status,
        expiry_status=expiry_status,
        expiring_within_days=expiring_within_days,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/batches/expiry/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_batch_expiry_report(
    product_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    expiry_status: Optional[str] = Query(None),
    expiring_within_days: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Batch Expiry Report to CSV."""
    report = await inventory_report_service.get_batch_expiry_report(
        db=db,
        product_id=product_id,
        status=status,
        expiry_status=expiry_status,
        expiring_within_days=expiring_within_days,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("batches", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=batch_expiry_report.csv"},
    )


# =============================================================================
# 6. SERIAL INVENTORY REPORT & EXPORT
# =============================================================================
@router.get(
    "/serials",
    response_model=PaginatedSerialInventoryReportResponse,
    dependencies=[Depends(has_any_permission("inventory.report.serial.read", "inventory.reports.read"))],
)
async def get_serial_inventory_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    batch_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Individual Serial Number Status and Location Report."""
    return await inventory_report_service.get_serial_inventory_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        batch_id=batch_id,
        status=status,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/serials/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_serial_inventory_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    batch_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Serial Inventory Report to CSV."""
    report = await inventory_report_service.get_serial_inventory_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        batch_id=batch_id,
        status=status,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("serials", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=serial_inventory_report.csv"},
    )


# =============================================================================
# 7. STOCK RESERVATIONS REPORT & EXPORT
# =============================================================================
@router.get(
    "/reservations",
    response_model=PaginatedStockReservationReportResponse,
    dependencies=[Depends(has_any_permission("inventory.report.reservation.read", "inventory.reports.read"))],
)
async def get_reservation_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    reserved_for_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Read-Only Stock Reservation Visibility Report."""
    return await inventory_report_service.get_reservation_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        status=status,
        reserved_for_type=reserved_for_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/reservations/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_reservation_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    reserved_for_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Stock Reservation Report to CSV."""
    report = await inventory_report_service.get_reservation_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        status=status,
        reserved_for_type=reserved_for_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("reservations", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_reservation_report.csv"},
    )


# =============================================================================
# 8. AVAILABLE STOCK REPORT & EXPORT
# =============================================================================
@router.get(
    "/availability",
    response_model=PaginatedAvailableStockReportResponse,
    dependencies=[Depends(has_any_permission("inventory.report.stock.read", "inventory.reports.read"))],
)
async def get_available_stock_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    tracking_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Dedicated Stock Availability Model (On-Hand minus Active Reservations)."""
    return await inventory_report_service.get_available_stock_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        category_id=category_id,
        tracking_type=tracking_type,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/availability/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_available_stock_report(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    tracking_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Stock Availability Report to CSV."""
    report = await inventory_report_service.get_available_stock_report(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        category_id=category_id,
        tracking_type=tracking_type,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("availability", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=available_stock_report.csv"},
    )


# =============================================================================
# 9. LOW STOCK / REORDER REPORT & EXPORT
# =============================================================================
@router.get(
    "/low-stock",
    response_model=PaginatedLowStockReportResponse,
    dependencies=[Depends(has_any_permission("inventory.report.stock.read", "inventory.reports.read"))],
)
async def get_low_stock_report(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    below_reorder_only: bool = Query(False),
    below_min_only: bool = Query(False),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Low Stock and Reorder Threshold Monitoring Report."""
    return await inventory_report_service.get_low_stock_report(
        db=db,
        warehouse_id=warehouse_id,
        category_id=category_id,
        below_reorder_only=below_reorder_only,
        below_min_only=below_min_only,
        search=search,
        page=page,
        size=size,
    )


@router.get(
    "/low-stock/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_low_stock_report(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    below_reorder_only: bool = Query(False),
    below_min_only: bool = Query(False),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Low Stock Report to CSV."""
    report = await inventory_report_service.get_low_stock_report(
        db=db,
        warehouse_id=warehouse_id,
        category_id=category_id,
        below_reorder_only=below_reorder_only,
        below_min_only=below_min_only,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("low-stock", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=low_stock_report.csv"},
    )


# =============================================================================
# 10. INVENTORY MOVEMENT ANALYTICS
# =============================================================================
@router.get(
    "/analytics",
    response_model=InventoryMovementAnalyticsResponse,
    dependencies=[Depends(has_any_permission("inventory.report.analytics.read", "inventory.reports.read", "inventory.analytics.read"))],
)
async def get_inventory_movement_analytics(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Historical Inventory Movement Analytics (Breakdowns by Type, Category, Warehouse, Timeline)."""
    return await inventory_report_service.get_movement_analytics(
        db=db,
        date_from=date_from,
        date_to=date_to,
        product_id=product_id,
        warehouse_id=warehouse_id,
        category_id=category_id,
    )


# =============================================================================
# 11. INVENTORY AGING REPORT & EXPORT
# =============================================================================
@router.get(
    "/aging",
    dependencies=[Depends(has_any_permission("inventory.report.stock.read", "inventory.reports.read"))],
)
async def get_inventory_aging_report(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    aging_bucket: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: Optional[int] = Query(None),
    size: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve Inventory Aging Report (0-30, 31-60, 61-90, 90+ days).
    Supports both legacy flat list format and v0.6.4 paginated response format.
    """
    if page is not None or size is not None or aging_bucket is not None or search is not None:
        p = page or 1
        s = size or 50
        return await inventory_report_service.get_inventory_aging_report_paginated(
            db=db,
            warehouse_id=warehouse_id,
            aging_bucket=aging_bucket,
            search=search,
            page=p,
            size=s,
        )
    return await inventory_report_service.get_inventory_aging_report(db, warehouse_id=warehouse_id)


@router.get(
    "/aging/export",
    dependencies=[Depends(has_any_permission("inventory.report.export", "inventory.reports.read"))],
)
async def export_inventory_aging_report(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    aging_bucket: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export Inventory Aging Report to CSV."""
    report = await inventory_report_service.get_inventory_aging_report_paginated(
        db=db,
        warehouse_id=warehouse_id,
        aging_bucket=aging_bucket,
        search=search,
        page=1,
        size=5000,
    )
    csv_data = inventory_report_service.export_report_to_csv("aging", report.items)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_aging_report.csv"},
    )


# =============================================================================
# 12. EXECUTIVE DASHBOARD SUMMARY
# =============================================================================
@router.get(
    "/dashboard",
    response_model=InventoryExecutiveDashboardResponse,
    dependencies=[Depends(has_any_permission("inventory.report.analytics.read", "inventory.reports.read", "inventory.analytics.read"))],
)
async def get_inventory_executive_dashboard(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Executive Inventory Dashboard KPIs & Top Moving SKU Metrics."""
    return await inventory_report_service.get_executive_dashboard_summary(
        db=db,
        date_from=date_from,
        date_to=date_to,
    )


# =============================================================================
# BACKWARD COMPATIBILITY ENDPOINTS
# =============================================================================
@router.get(
    "/valuation",
    response_model=List[StockValuationItem],
    dependencies=[Depends(has_any_permission("inventory.reports.read", "inventory.report.stock.read"))],
)
async def get_stock_valuation_report(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Stock Valuation Report (Legacy Display Metadata)."""
    return await inventory_report_service.get_stock_valuation_report(db, warehouse_id=warehouse_id)


@router.get(
    "/movement",
    response_model=List[MovementAnalysisItem],
    dependencies=[Depends(has_any_permission("inventory.reports.read", "inventory.report.movement.read"))],
)
async def get_movement_analysis_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Fast Moving, Slow Moving, and Dead Stock Analysis Report (Legacy)."""
    return await inventory_report_service.get_movement_analysis_report(db)
