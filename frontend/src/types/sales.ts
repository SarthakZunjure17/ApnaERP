export type SalesOrderStatus = 'Draft' | 'Confirmed' | 'Processing' | 'Completed' | 'Cancelled';
export type PaymentStatus = 'Paid' | 'Pending' | 'Overdue' | 'Partially Paid';
export type FulfillmentStatus = 'Unfulfilled' | 'Processing' | 'Shipped' | 'Delivered' | 'Cancelled';

export interface SalesOrderItem {
  id: string;
  item_name: string;
  description: string;
  sku: string;
  quantity: number;
  unit_price: number;
  formatted_unit_price: string;
  tax_rate: number;
  subtotal: number;
  formatted_subtotal: string;
}

export interface SalesOrderTimelineStep {
  id: string;
  timestamp: string;
  title: string;
  description: string;
  user_name?: string;
  user_avatar?: string;
  status: 'completed' | 'current' | 'pending';
}

export interface SalesOrderComment {
  id: string;
  author_name: string;
  author_avatar?: string;
  time_ago: string;
  content: string;
  is_system?: boolean;
}

export interface SalesOrderDetail {
  id: string;
  order_number: string;
  date: string;
  status: SalesOrderStatus;
  payment_status: PaymentStatus;
  fulfillment_status: FulfillmentStatus;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  customer_company: string;
  billing_address: string;
  shipping_address: string;
  region: string;
  sales_rep: {
    name: string;
    email: string;
    avatar_url: string;
    designation: string;
  };
  expected_delivery: string;
  payment_terms: string;
  shipping_carrier?: string;
  tracking_number?: string;
  items: SalesOrderItem[];
  subtotal: number;
  formatted_subtotal: string;
  tax_amount: number;
  formatted_tax: string;
  shipping_amount: number;
  formatted_shipping: string;
  discount_amount: number;
  formatted_discount: string;
  total_amount: number;
  formatted_total: string;
  timeline: SalesOrderTimelineStep[];
  comments: SalesOrderComment[];
}

export interface SalesOrderListItem {
  id: string;
  order_number: string;
  date: string;
  customer_name: string;
  customer_initials: string;
  region: string;
  amount: number;
  formatted_amount: string;
  status: SalesOrderStatus;
  payment_status: PaymentStatus;
  fulfillment_status: FulfillmentStatus;
  sales_rep_name: string;
  sales_rep_avatar?: string;
  items_count: number;
  expected_delivery: string;
}

export interface SalesMetrics {
  total_orders_count: number;
  total_revenue_formatted: string;
  pending_fulfillment_count: number;
  average_order_value_formatted: string;
}

export interface SalesOrderFilters {
  search?: string;
  customer?: string;
  region?: string;
  fulfillment?: string;
  paymentStatus?: string;
  status?: string;
}
