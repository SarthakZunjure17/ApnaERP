export interface POLineItem {
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

export interface POApprovalStep {
  id: string;
  timestamp: string;
  title: string;
  description: string;
  user_name?: string;
  user_avatar?: string;
  status: 'completed' | 'current' | 'pending';
}

export interface POComment {
  id: string;
  author_name: string;
  author_avatar?: string;
  time_ago: string;
  content: string;
  is_system?: boolean;
}

export interface PurchaseOrderDetail {
  id: string;
  po_number: string;
  status: 'Draft' | 'Pending Approval' | 'Approved' | 'Rejected' | 'Cancelled';
  supplier_name: string;
  contact_person: string;
  contact_email: string;
  supplier_address: string;
  ship_to_address: string;
  expected_delivery: string;
  payment_terms: string;
  items: POLineItem[];
  subtotal: number;
  formatted_subtotal: string;
  tax_amount: number;
  formatted_tax: string;
  shipping_amount: number;
  formatted_shipping: string;
  total_amount: number;
  formatted_total: string;
  timeline: POApprovalStep[];
  comments: POComment[];
}

export interface PurchaseOrderListItem {
  id: string;
  po_number: string;
  date: string;
  supplier_name: string;
  supplier_initials: string;
  amount: number;
  formatted_amount: string;
  expected_date: string;
  status: 'Draft' | 'Pending Approval' | 'Approved' | 'Rejected';
  approver_name: string;
  approver_avatar?: string;
}
