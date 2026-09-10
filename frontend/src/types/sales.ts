export interface CustomerItem {
  id: string;
  name: string;
  code: string;
  customer_type: 'Individual' | 'Corporate' | 'Enterprise';
  email?: string;
  phone?: string;
  tax_identifier?: string;
  credit_limit: number;
  credit_days: number;
  is_active: boolean;
  city?: string;
  country?: string;
}

export interface SOLineItem {
  id?: string;
  product_id: string;
  product_sku?: string;
  product_name?: string;
  quantity: number;
  unit_price: number;
  discount_amount?: number;
  tax_rate?: number;
  total_price?: number;
  fulfilled_quantity?: number;
}

export interface SalesOrderListItem {
  id: string;
  order_number: string;
  order_date: string;
  customer_id: string;
  customer_name: string;
  warehouse_id?: string;
  warehouse_name?: string;
  total_amount: number;
  status: 'Draft' | 'Submitted' | 'Approved' | 'Rejected' | 'In Production' | 'Dispatched' | 'Delivered' | 'Cancelled' | 'Closed';
  created_at?: string;
}

export interface SalesOrderDetail extends SalesOrderListItem {
  payment_terms?: string;
  currency_code?: string;
  notes?: string;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  items: SOLineItem[];
}

export interface SalesOrderCreatePayload {
  customer_id: string;
  warehouse_id?: string;
  order_date: string;
  expected_delivery_date?: string;
  payment_terms?: string;
  currency_code?: string;
  notes?: string;
  items: Array<{
    product_id: string;
    quantity: number;
    unit_price: number;
    discount_amount?: number;
    tax_rate?: number;
  }>;
}

export interface SalesQuotationItem {
  id: string;
  quotation_number: string;
  customer_id: string;
  customer_name: string;
  quotation_date: string;
  expiry_date?: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  status: 'Draft' | 'Sent' | 'Approved' | 'Rejected' | 'Converted' | 'Expired' | 'Cancelled';
  created_at: string;
}

export interface DeliveryOrderItem {
  id: string;
  delivery_number: string;
  sales_order_id: string;
  sales_order_number?: string;
  customer_id: string;
  customer_name: string;
  dispatch_date: string;
  status: 'Draft' | 'Picked' | 'Packed' | 'Dispatched' | 'Delivered' | 'Cancelled';
  tracking_number?: string;
  carrier?: string;
  created_at: string;
}
