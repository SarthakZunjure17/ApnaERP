import { api } from './api';
import { PurchaseOrderListItem, PurchaseOrderDetail } from '../types/procurement';

const MOCK_PO_DETAIL: PurchaseOrderDetail = {
  id: 'po-2023-0892',
  po_number: 'PO-2023-0892',
  status: 'Pending Approval',
  supplier_name: 'TechSolutions Global Inc.',
  contact_person: 'Sarah Jenkins',
  contact_email: 'sarah.j@techsolutions.com',
  supplier_address: '1440 Silicon Valley Blvd,\nSan Jose, CA 95112',
  ship_to_address: 'Main Warehouse\nBlock C, Industrial Park,\nAustin, TX 78744',
  expected_delivery: 'Oct 24, 2023',
  payment_terms: 'Net 30',
  items: [
    {
      id: 'item-1',
      item_name: 'Enterprise Server Racks',
      description: '42U Standard enclosure',
      sku: 'HW-SR-42U',
      quantity: 12,
      unit_price: 850.0,
      formatted_unit_price: '$850.00',
      tax_rate: 8,
      subtotal: 10200.0,
      formatted_subtotal: '$10,200.00',
    },
    {
      id: 'item-2',
      item_name: 'Network Switches 48-port',
      description: 'Managed Layer 3',
      sku: 'NT-SW-48M',
      quantity: 6,
      unit_price: 1200.0,
      formatted_unit_price: '$1,200.00',
      tax_rate: 8,
      subtotal: 7200.0,
      formatted_subtotal: '$7,200.00',
    },
    {
      id: 'item-3',
      item_name: 'Fiber Optic Cable Bundle',
      description: 'OM4 Multimode 50m',
      sku: 'CB-FO-OM4',
      quantity: 24,
      unit_price: 150.0,
      formatted_unit_price: '$150.00',
      tax_rate: 8,
      subtotal: 3600.0,
      formatted_subtotal: '$3,600.00',
    },
  ],
  subtotal: 21000.0,
  formatted_subtotal: '$21,000.00',
  tax_amount: 1680.0,
  formatted_tax: '$1,680.00',
  shipping_amount: 450.0,
  formatted_shipping: '$450.00',
  total_amount: 23130.0,
  formatted_total: '$23,130.00',
  timeline: [
    {
      id: 'tl-1',
      timestamp: 'Oct 12, 2023 • 09:41 AM',
      title: 'PO Created',
      description: 'Marcus Johnson',
      user_name: 'Marcus Johnson',
      user_avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=50&auto=format&fit=crop&q=80',
      status: 'completed',
    },
    {
      id: 'tl-2',
      timestamp: 'Oct 12, 2023 • 10:15 AM',
      title: 'Sent for Approval',
      description: 'Automated workflow triggered',
      status: 'completed',
    },
    {
      id: 'tl-3',
      timestamp: 'Current State',
      title: 'Pending Manager Approval',
      description: 'Waiting on ERP Admin',
      status: 'current',
    },
  ],
  comments: [
    {
      id: 'c-1',
      author_name: 'Marcus J.',
      time_ago: 'Yesterday',
      content: 'Expedited shipping requested for the server racks due to client deadline.',
      is_system: false,
    },
    {
      id: 'c-2',
      author_name: 'System',
      time_ago: 'Yesterday',
      content: 'Budget check passed for department IT-Infrastructure.',
      is_system: true,
    },
  ],
};

const MOCK_PO_LIST: PurchaseOrderListItem[] = [
  {
    id: 'po-1042',
    po_number: 'PO-2024-1042',
    date: 'Oct 24, 2024',
    supplier_name: 'Acme Corp',
    supplier_initials: 'AC',
    amount: 125000.0,
    formatted_amount: '$125,000.00',
    expected_date: 'Nov 15, 2024',
    status: 'Pending Approval',
    approver_name: 'Sarah J.',
    approver_avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80',
  },
  {
    id: 'po-1041',
    po_number: 'PO-2024-1041',
    date: 'Oct 22, 2024',
    supplier_name: 'Global Industries',
    supplier_initials: 'GL',
    amount: 45200.5,
    formatted_amount: '$45,200.50',
    expected_date: 'Nov 01, 2024',
    status: 'Approved',
    approver_name: 'Michael T.',
    approver_avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=50&auto=format&fit=crop&q=80',
  },
  {
    id: 'po-1040',
    po_number: 'PO-2024-1040',
    date: 'Oct 20, 2024',
    supplier_name: 'TechSolutions Inc',
    supplier_initials: 'TS',
    amount: 8500.0,
    formatted_amount: '$8,500.00',
    expected_date: 'TBD',
    status: 'Draft',
    approver_name: 'Unassigned',
  },
  {
    id: 'po-1039',
    po_number: 'PO-2024-1039',
    date: 'Oct 18, 2024',
    supplier_name: 'Acme Corp',
    supplier_initials: 'AC',
    amount: 210000.0,
    formatted_amount: '$210,000.00',
    expected_date: '--',
    status: 'Rejected',
    approver_name: 'Sarah J.',
    approver_avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80',
  },
];

export const procurementService = {
  getPurchaseOrders: async (filters?: {
    supplier?: string;
    status?: string;
    dateRange?: string;
  }): Promise<{ items: PurchaseOrderListItem[]; total: number; totalPendingAmount: string }> => {
    try {
      const response = await api.get('/procurement/orders');
      if (response.data && Array.isArray(response.data.items)) {
        return response.data;
      }
      return filterMockOrders(filters);
    } catch {
      return filterMockOrders(filters);
    }
  },

  getPurchaseOrderById: async (id: string): Promise<PurchaseOrderDetail> => {
    try {
      const response = await api.get(`/procurement/orders/${id}`);
      if (response.data) return response.data;
      return MOCK_PO_DETAIL;
    } catch {
      return MOCK_PO_DETAIL;
    }
  },

  approvePurchaseOrder: async (id: string): Promise<PurchaseOrderDetail> => {
    try {
      const response = await api.post(`/procurement/orders/${id}/approve`);
      return response.data;
    } catch {
      return {
        ...MOCK_PO_DETAIL,
        status: 'Approved',
      };
    }
  },

  rejectPurchaseOrder: async (id: string, reason?: string): Promise<PurchaseOrderDetail> => {
    try {
      const response = await api.post(`/procurement/orders/${id}/reject`, { reason });
      return response.data;
    } catch {
      return {
        ...MOCK_PO_DETAIL,
        status: 'Rejected',
      };
    }
  },

  addComment: async (id: string, content: string): Promise<PurchaseOrderDetail> => {
    const newComment = {
      id: `c-${Date.now()}`,
      author_name: 'ERP Admin',
      time_ago: 'Just now',
      content,
      is_system: false,
    };
    return {
      ...MOCK_PO_DETAIL,
      comments: [...MOCK_PO_DETAIL.comments, newComment],
    };
  },
};

function filterMockOrders(filters?: { supplier?: string; status?: string }) {
  let items = [...MOCK_PO_LIST];
  if (filters?.supplier && filters.supplier !== 'All Suppliers') {
    items = items.filter((po) => po.supplier_name.toLowerCase().includes(filters.supplier!.toLowerCase()));
  }
  if (filters?.status && filters.status !== 'All') {
    items = items.filter((po) => po.status.toLowerCase().includes(filters.status!.toLowerCase()));
  }
  return {
    items,
    total: 124,
    totalPendingAmount: '$450,230.00',
  };
}
