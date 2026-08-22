import { api } from './api';
import { PurchaseOrderListItem, PurchaseOrderDetail } from '../types/procurement';

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
    expected_date: 'Nov 25, 2024',
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

const MOCK_PO_DETAILS_MAP: Record<string, PurchaseOrderDetail> = {
  'po-1042': {
    id: 'po-1042',
    po_number: 'PO-2024-1042',
    status: 'Pending Approval',
    supplier_name: 'Acme Corp',
    contact_person: 'Sarah Jenkins',
    contact_email: 'sarah.j@acmecorp.com',
    supplier_address: '1440 Silicon Valley Blvd,\nSan Jose, CA 95112',
    ship_to_address: 'Main Warehouse\nBlock C, Industrial Park,\nAustin, TX 78744',
    expected_delivery: 'Nov 15, 2024',
    payment_terms: 'Net 30',
    items: [
      {
        id: 'item-1',
        item_name: 'Enterprise Server Racks 42U',
        description: '42U Standard enclosure with dual power distribution',
        sku: 'HW-SR-42U',
        quantity: 50,
        unit_price: 1850.0,
        formatted_unit_price: '$1,850.00',
        tax_rate: 8,
        subtotal: 92500.0,
        formatted_subtotal: '$92,500.00',
      },
      {
        id: 'item-2',
        item_name: 'Network Switches 48-port PoE+',
        description: 'Managed Layer 3 enterprise switch',
        sku: 'NT-SW-48M',
        quantity: 20,
        unit_price: 1400.0,
        formatted_unit_price: '$1,400.00',
        tax_rate: 8,
        subtotal: 28000.0,
        formatted_subtotal: '$28,000.00',
      },
      {
        id: 'item-3',
        item_name: 'Fiber Optic Cable Spool',
        description: 'OM4 Multimode 500m spool',
        sku: 'CB-FO-OM4',
        quantity: 30,
        unit_price: 150.0,
        formatted_unit_price: '$150.00',
        tax_rate: 8,
        subtotal: 4500.0,
        formatted_subtotal: '$4,500.00',
      },
    ],
    subtotal: 125000.0,
    formatted_subtotal: '$125,000.00',
    tax_amount: 10000.0,
    formatted_tax: '$10,000.00',
    shipping_amount: 1200.0,
    formatted_shipping: '$1,200.00',
    total_amount: 136200.0,
    formatted_total: '$136,200.00',
    timeline: [
      {
        id: 'tl-1',
        timestamp: 'Oct 24, 2024 • 09:41 AM',
        title: 'PO Created',
        description: 'Marcus Johnson',
        user_name: 'Marcus Johnson',
        user_avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=50&auto=format&fit=crop&q=80',
        status: 'completed',
      },
      {
        id: 'tl-2',
        timestamp: 'Oct 24, 2024 • 10:15 AM',
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
        content: 'Expedited delivery requested for data center expansion.',
      },
      {
        id: 'c-2',
        author_name: 'System',
        time_ago: 'Yesterday',
        content: 'Budget check passed for department Infrastructure.',
        is_system: true,
      },
    ],
  },
  'po-1041': {
    id: 'po-1041',
    po_number: 'PO-2024-1041',
    status: 'Approved',
    supplier_name: 'Global Industries',
    contact_person: 'Michael Torres',
    contact_email: 'm.torres@globalind.com',
    supplier_address: '800 Industrial Highway,\nChicago, IL 60607',
    ship_to_address: 'Regional Depot\nBuilding 4, Dock 12,\nDallas, TX 75201',
    expected_delivery: 'Nov 01, 2024',
    payment_terms: 'Net 45',
    items: [
      {
        id: 'item-10',
        item_name: 'Precision Hydraulic Valves',
        description: 'High pressure stainless steel valve assembly',
        sku: 'IND-VAL-88',
        quantity: 120,
        unit_price: 350.0,
        formatted_unit_price: '$350.00',
        tax_rate: 8,
        subtotal: 42000.0,
        formatted_subtotal: '$42,000.00',
      },
      {
        id: 'item-11',
        item_name: 'Industrial Sensor Calibration Kits',
        description: 'Field diagnostic calibration probes',
        sku: 'IND-SEN-KIT',
        quantity: 8,
        unit_price: 400.0,
        formatted_unit_price: '$400.00',
        tax_rate: 8,
        subtotal: 3200.5,
        formatted_subtotal: '$3,200.50',
      },
    ],
    subtotal: 45200.5,
    formatted_subtotal: '$45,200.50',
    tax_amount: 3616.04,
    formatted_tax: '$3,616.04',
    shipping_amount: 650.0,
    formatted_shipping: '$650.00',
    total_amount: 49466.54,
    formatted_total: '$49,466.54',
    timeline: [
      {
        id: 'tl-10',
        timestamp: 'Oct 22, 2024 • 11:00 AM',
        title: 'PO Created',
        description: 'Michael Torres',
        status: 'completed',
      },
      {
        id: 'tl-11',
        timestamp: 'Oct 22, 2024 • 03:30 PM',
        title: 'Approved by ERP Admin',
        description: 'Sign-off complete',
        status: 'completed',
      },
    ],
    comments: [
      {
        id: 'c-10',
        author_name: 'Michael T.',
        time_ago: '3 days ago',
        content: 'Stock replenishment for factory line 2.',
      },
    ],
  },
};

export const procurementService = {
  getPurchaseOrders: async (filters?: {
    supplier?: string;
    status?: string;
    dateRange?: string;
  }): Promise<{ items: PurchaseOrderListItem[]; total: number; totalPendingAmount: string }> => {
    try {
      const response = await api.get('/api/v1/procurement/orders', { params: filters });
      if (response.data && typeof response.data === 'object' && Array.isArray(response.data.items)) {
        return response.data;
      }
      return filterMockOrders(filters);
    } catch {
      return filterMockOrders(filters);
    }
  },

  getPurchaseOrderById: async (id: string): Promise<PurchaseOrderDetail | null> => {
    try {
      const response = await api.get(`/api/v1/procurement/orders/${id}`);
      if (response.data && typeof response.data === 'object' && response.data.id) {
        return response.data;
      }
      return getMockPoDetailById(id);
    } catch {
      return getMockPoDetailById(id);
    }
  },

  createPurchaseOrder: async (poData: {
    supplier_name: string;
    amount: number;
    expected_date: string;
  }): Promise<PurchaseOrderListItem> => {
    const newId = `po-${Date.now()}`;
    const newPoNumber = `PO-2024-${Math.floor(1050 + Math.random() * 900)}`;
    const initials = poData.supplier_name
      .split(' ')
      .map((w) => w[0])
      .slice(0, 2)
      .join('')
      .toUpperCase() || 'PO';

    const newListItem: PurchaseOrderListItem = {
      id: newId,
      po_number: newPoNumber,
      date: 'Today',
      supplier_name: poData.supplier_name,
      supplier_initials: initials,
      amount: poData.amount,
      formatted_amount: `$${poData.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      expected_date: poData.expected_date || 'Nov 30, 2024',
      status: 'Pending Approval',
      approver_name: 'ERP Admin',
    };

    MOCK_PO_LIST.unshift(newListItem);

    const newDetail: PurchaseOrderDetail = {
      id: newId,
      po_number: newPoNumber,
      status: 'Pending Approval',
      supplier_name: poData.supplier_name,
      contact_person: 'Supplier Account Representative',
      contact_email: `orders@${poData.supplier_name.toLowerCase().replace(/[^a-z]/g, '')}.com`,
      supplier_address: `100 Commercial Blvd,\nCity Center Depot`,
      ship_to_address: `Main Warehouse\nBlock C, Industrial Park,\nAustin, TX 78744`,
      expected_delivery: poData.expected_date || 'Nov 30, 2024',
      payment_terms: 'Net 30',
      items: [
        {
          id: `item-${Date.now()}`,
          item_name: `Procured Inventory Batch (${poData.supplier_name})`,
          description: 'Standard supplier procurement package',
          sku: `PRC-${Date.now().toString().slice(-6)}`,
          quantity: 1,
          unit_price: poData.amount,
          formatted_unit_price: `$${poData.amount.toFixed(2)}`,
          tax_rate: 8,
          subtotal: poData.amount,
          formatted_subtotal: `$${poData.amount.toFixed(2)}`,
        },
      ],
      subtotal: poData.amount,
      formatted_subtotal: `$${poData.amount.toFixed(2)}`,
      tax_amount: poData.amount * 0.08,
      formatted_tax: `$${(poData.amount * 0.08).toFixed(2)}`,
      shipping_amount: 350.0,
      formatted_shipping: '$350.00',
      total_amount: poData.amount * 1.08 + 350,
      formatted_total: `$${(poData.amount * 1.08 + 350).toFixed(2)}`,
      timeline: [
        {
          id: `tl-${Date.now()}`,
          timestamp: 'Today',
          title: 'PO Created',
          description: 'Submitted for manager review',
          status: 'completed',
        },
        {
          id: `tl-${Date.now()}-2`,
          timestamp: 'Current State',
          title: 'Pending Manager Approval',
          description: 'Waiting on ERP Admin',
          status: 'current',
        },
      ],
      comments: [
        {
          id: `c-${Date.now()}`,
          author_name: 'ERP Admin',
          time_ago: 'Just now',
          content: 'Purchase order generated and routed for approval.',
        },
      ],
    };

    MOCK_PO_DETAILS_MAP[newId] = newDetail;
    return newListItem;
  },

  approvePurchaseOrder: async (id: string): Promise<PurchaseOrderDetail | null> => {
    try {
      const response = await api.post(`/api/v1/procurement/orders/${id}/approve`);
      if (response.data && typeof response.data === 'object' && response.data.id) {
        return response.data;
      }
    } catch {
      // Continue to local update
    }

    const po = getMockPoDetailById(id);
    if (!po) return null;
    po.status = 'Approved';
    
    // Also update in list
    const cleanId = id.trim().toLowerCase();
    const foundListItem = MOCK_PO_LIST.find(
      (p) => p.id.toLowerCase() === cleanId || p.po_number.toLowerCase() === cleanId
    );
    if (foundListItem) {
      foundListItem.status = 'Approved';
    }

    MOCK_PO_DETAILS_MAP[po.id] = po;
    return po;
  },

  rejectPurchaseOrder: async (id: string, reason?: string): Promise<PurchaseOrderDetail | null> => {
    try {
      const response = await api.post(`/api/v1/procurement/orders/${id}/reject`, { reason });
      if (response.data && typeof response.data === 'object' && response.data.id) {
        return response.data;
      }
    } catch {
      // Continue to local update
    }

    const po = getMockPoDetailById(id);
    if (!po) return null;
    po.status = 'Rejected';
    if (reason) {
      po.comments.unshift({
        id: `c-${Date.now()}`,
        author_name: 'ERP Admin',
        time_ago: 'Just now',
        content: `Rejected: ${reason}`,
      });
    }

    const cleanId = id.trim().toLowerCase();
    const foundListItem = MOCK_PO_LIST.find(
      (p) => p.id.toLowerCase() === cleanId || p.po_number.toLowerCase() === cleanId
    );
    if (foundListItem) {
      foundListItem.status = 'Rejected';
    }

    MOCK_PO_DETAILS_MAP[po.id] = po;
    return po;
  },

  addComment: async (id: string, content: string): Promise<PurchaseOrderDetail | null> => {
    const po = getMockPoDetailById(id);
    if (!po) return null;
    const newComment = {
      id: `c-${Date.now()}`,
      author_name: 'ERP Admin',
      time_ago: 'Just now',
      content,
      is_system: false,
    };
    po.comments.unshift(newComment);
    MOCK_PO_DETAILS_MAP[po.id] = po;
    return po;
  },
};

function filterMockOrders(filters?: { supplier?: string; status?: string }) {
  let items = [...MOCK_PO_LIST];
  if (filters?.supplier && filters.supplier !== 'All Suppliers' && filters.supplier !== 'All') {
    items = items.filter((po) => po.supplier_name.toLowerCase() === filters.supplier!.toLowerCase());
  }
  if (filters?.status && filters.status !== 'All' && filters.status !== 'All Statuses') {
    items = items.filter((po) => po.status.toLowerCase() === filters.status!.toLowerCase());
  }

  const pendingSum = items
    .filter((po) => po.status === 'Pending Approval')
    .reduce((sum, po) => sum + po.amount, 0);

  return {
    items,
    total: items.length,
    totalPendingAmount: `$${pendingSum.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
  };
}

function getMockPoDetailById(id: string): PurchaseOrderDetail | null {
  if (!id) return null;
  const cleanId = id.trim().toLowerCase();

  // Direct match in map (case-insensitive keys or po_number)
  for (const [key, detail] of Object.entries(MOCK_PO_DETAILS_MAP)) {
    if (key.toLowerCase() === cleanId || detail.po_number.toLowerCase() === cleanId) {
      return detail;
    }
  }

  const foundInList = MOCK_PO_LIST.find(
    (p) => p.id.toLowerCase() === cleanId || p.po_number.toLowerCase() === cleanId
  );
  if (foundInList) {
    const po: PurchaseOrderDetail = {
      id: foundInList.id,
      po_number: foundInList.po_number,
      status: foundInList.status,
      supplier_name: foundInList.supplier_name,
      contact_person: `${foundInList.supplier_name} Representative`,
      contact_email: `contact@${foundInList.supplier_name.toLowerCase().replace(/[^a-z]/g, '')}.com`,
      supplier_address: `1200 Commercial Park,\nCity Center`,
      ship_to_address: `Main Warehouse\nBlock C, Industrial Park,\nAustin, TX 78744`,
      expected_delivery: foundInList.expected_date,
      payment_terms: 'Net 30',
      items: [
        {
          id: `item-${foundInList.id}-1`,
          item_name: `Procured Materials Package (${foundInList.supplier_name})`,
          description: 'Standard supplier equipment and materials delivery',
          sku: 'MAT-GEN-001',
          quantity: 1,
          unit_price: foundInList.amount,
          formatted_unit_price: foundInList.formatted_amount,
          tax_rate: 8,
          subtotal: foundInList.amount,
          formatted_subtotal: foundInList.formatted_amount,
        },
      ],
      subtotal: foundInList.amount,
      formatted_subtotal: foundInList.formatted_amount,
      tax_amount: foundInList.amount * 0.08,
      formatted_tax: `$${(foundInList.amount * 0.08).toFixed(2)}`,
      shipping_amount: 450.0,
      formatted_shipping: '$450.00',
      total_amount: foundInList.amount * 1.08 + 450,
      formatted_total: `$${(foundInList.amount * 1.08 + 450).toFixed(2)}`,
      timeline: [
        {
          id: 'tl-dyn-1',
          timestamp: foundInList.date,
          title: 'PO Created',
          description: 'Automated requisition',
          status: 'completed',
        },
        {
          id: 'tl-dyn-2',
          timestamp: 'Current State',
          title: `Status: ${foundInList.status}`,
          description: foundInList.approver_name !== 'Unassigned' ? `Assigned to ${foundInList.approver_name}` : 'Awaiting routing',
          status: 'current',
        },
      ],
      comments: [
        {
          id: 'c-dyn-1',
          author_name: 'ERP System',
          time_ago: 'Recently',
          content: `Purchase order logged for ${foundInList.supplier_name}.`,
          is_system: true,
        },
      ],
    };
    MOCK_PO_DETAILS_MAP[foundInList.id] = po;
    return po;
  }

  // Return null if not found
  return null;
}
