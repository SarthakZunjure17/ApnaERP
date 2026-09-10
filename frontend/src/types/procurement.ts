export interface SupplierItem {
  id: string;
  name: string;
  code: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  tax_identifier?: string;
  rating?: number;
  is_active: boolean;
}

export interface POLineItem {
  id?: string;
  product_id: string;
  product_sku?: string;
  product_name?: string;
  quantity: number;
  unit_price: number;
  tax_rate?: number;
  discount_amount?: number;
  total_price?: number;
  received_quantity?: number;
}

export interface PurchaseOrderListItem {
  id: string;
  po_number: string;
  order_date: string;
  supplier_id: string;
  supplier_name: string;
  warehouse_id?: string;
  warehouse_name?: string;
  total_amount: number;
  expected_delivery_date?: string;
  status: 'Draft' | 'Submitted' | 'Approved' | 'Rejected' | 'Dispatched' | 'Received' | 'Cancelled' | 'Closed';
  created_at?: string;
}

export interface PurchaseOrderDetail extends PurchaseOrderListItem {
  payment_terms?: string;
  currency_code: string;
  notes?: string;
  subtotal: number;
  tax_amount: number;
  items: POLineItem[];
}

export interface PurchaseOrderCreatePayload {
  supplier_id: string;
  warehouse_id: string;
  order_date: string;
  expected_delivery_date?: string;
  payment_terms?: string;
  currency_code?: string;
  notes?: string;
  items: Array<{
    product_id: string;
    quantity: number;
    unit_price: number;
    tax_rate?: number;
    discount_amount?: number;
  }>;
}

export interface PurchaseRequisitionItem {
  id: string;
  pr_number: string;
  requisition_date: string;
  department_id?: string;
  department_name?: string;
  status: 'Draft' | 'Submitted' | 'Approved' | 'Rejected' | 'Ordered' | 'Cancelled';
  total_estimated_amount: number;
  created_at: string;
}

export interface RFQItem {
  id: string;
  rfq_number: string;
  issue_date: string;
  close_date?: string;
  status: 'Draft' | 'Sent' | 'Closed' | 'Cancelled';
  title: string;
  created_at: string;
}
