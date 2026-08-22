import { api } from './api';
import {
  SalesOrderListItem,
  SalesOrderDetail,
  SalesMetrics,
  SalesOrderFilters,
  SalesOrderStatus,
} from '../types/sales';

const MOCK_SALES_ORDERS_LIST: SalesOrderListItem[] = [
  {
    id: 'so-1001',
    order_number: 'SO-2024-1001',
    date: 'Oct 25, 2024',
    customer_name: 'Nexus Corp Technologies',
    customer_initials: 'NC',
    region: 'North America',
    amount: 14500.0,
    formatted_amount: '$14,500.00',
    status: 'Confirmed',
    payment_status: 'Paid',
    fulfillment_status: 'Processing',
    sales_rep_name: 'Sarah Jenkins',
    sales_rep_avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80',
    items_count: 3,
    expected_delivery: 'Nov 02, 2024',
  },
  {
    id: 'so-1002',
    order_number: 'SO-2024-1002',
    date: 'Oct 24, 2024',
    customer_name: 'Apex Global Logistics',
    customer_initials: 'AG',
    region: 'Europe',
    amount: 32800.0,
    formatted_amount: '$32,800.00',
    status: 'Confirmed',
    payment_status: 'Pending',
    fulfillment_status: 'Unfulfilled',
    sales_rep_name: 'Amit Patel',
    sales_rep_avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=50&auto=format&fit=crop&q=80',
    items_count: 8,
    expected_delivery: 'Nov 05, 2024',
  },
  {
    id: 'so-1003',
    order_number: 'SO-2024-1003',
    date: 'Oct 23, 2024',
    customer_name: 'Vanguard Retail Systems',
    customer_initials: 'VR',
    region: 'Asia Pacific',
    amount: 8900.5,
    formatted_amount: '$8,900.50',
    status: 'Completed',
    payment_status: 'Paid',
    fulfillment_status: 'Delivered',
    sales_rep_name: 'Rahul Verma',
    sales_rep_avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=50&auto=format&fit=crop&q=80',
    items_count: 2,
    expected_delivery: 'Oct 28, 2024',
  },
  {
    id: 'so-1004',
    order_number: 'SO-2024-1004',
    date: 'Oct 22, 2024',
    customer_name: 'Solstice Enterprise Solutions',
    customer_initials: 'SE',
    region: 'North America',
    amount: 54200.0,
    formatted_amount: '$54,200.00',
    status: 'Processing',
    payment_status: 'Partially Paid',
    fulfillment_status: 'Shipped',
    sales_rep_name: 'Sarah Jenkins',
    sales_rep_avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80',
    items_count: 12,
    expected_delivery: 'Oct 30, 2024',
  },
  {
    id: 'so-1005',
    order_number: 'SO-2024-1005',
    date: 'Oct 20, 2024',
    customer_name: 'Horizon Digital Media',
    customer_initials: 'HD',
    region: 'Latin America',
    amount: 6300.0,
    formatted_amount: '$6,300.00',
    status: 'Draft',
    payment_status: 'Pending',
    fulfillment_status: 'Unfulfilled',
    sales_rep_name: 'Neha Gupta',
    sales_rep_avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=50&auto=format&fit=crop&q=80',
    items_count: 1,
    expected_delivery: 'Nov 12, 2024',
  },
];

const MOCK_SALES_DETAILS_MAP: Record<string, SalesOrderDetail> = {
  'so-1001': {
    id: 'so-1001',
    order_number: 'SO-2024-1001',
    date: 'Oct 25, 2024',
    status: 'Confirmed',
    payment_status: 'Paid',
    fulfillment_status: 'Processing',
    customer_name: 'Nexus Corp Technologies',
    customer_email: 'procurement@nexuscorp.io',
    customer_phone: '+1 (555) 234-8901',
    customer_company: 'Nexus Technologies Inc.',
    billing_address: 'Suite 400, 100 Innovation Way\nSan Francisco, CA 94107\nUnited States',
    shipping_address: 'Warehouse Gate B, 450 Logistics Blvd\nOakland, CA 94607\nUnited States',
    region: 'North America',
    sales_rep: {
      name: 'Sarah Jenkins',
      email: 'sarah.j@apnaerp.com',
      avatar_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80',
      designation: 'Senior Enterprise Sales Lead',
    },
    expected_delivery: 'Nov 02, 2024',
    payment_terms: 'Net 30 (Wire Transfer)',
    shipping_carrier: 'FedEx Express Freight',
    tracking_number: 'FX-889021345US',
    items: [
      {
        id: 'item-s1',
        item_name: 'Aura Wireless Headphones (Enterprise Pack)',
        description: 'Noise cancelling Bluetooth 5.3 headset with dock',
        sku: 'AU-WH-001',
        quantity: 30,
        unit_price: 299.0,
        formatted_unit_price: '$299.00',
        tax_rate: 8,
        subtotal: 8970.0,
        formatted_subtotal: '$8,970.00',
      },
      {
        id: 'item-s2',
        item_name: 'ErgoPro Office Chair (Midnight Black)',
        description: 'Adjustable lumbar support ergonomic mesh chair',
        sku: 'FUR-OC-992',
        quantity: 10,
        unit_price: 450.0,
        formatted_unit_price: '$450.00',
        tax_rate: 8,
        subtotal: 4500.0,
        formatted_subtotal: '$4,500.00',
      },
      {
        id: 'item-s3',
        item_name: 'Precision Wireless Mouse Bulk Bundle',
        description: 'Multi-device pairing optical mouse',
        sku: 'LOG-MW-500',
        quantity: 15,
        unit_price: 69.0,
        formatted_unit_price: '$69.00',
        tax_rate: 8,
        subtotal: 1035.0,
        formatted_subtotal: '$1,035.00',
      },
    ],
    subtotal: 14505.0,
    formatted_subtotal: '$14,505.00',
    tax_amount: 1160.4,
    formatted_tax: '$1,160.40',
    shipping_amount: 250.0,
    formatted_shipping: '$250.00',
    discount_amount: 1415.4,
    formatted_discount: '-$1,415.40',
    total_amount: 14500.0,
    formatted_total: '$14,500.00',
    timeline: [
      {
        id: 'st-1',
        timestamp: 'Oct 25, 2024 • 09:30 AM',
        title: 'Quotation Accepted',
        description: 'Customer approved Quote #Q-2024-0412',
        user_name: 'Sarah Jenkins',
        user_avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80',
        status: 'completed',
      },
      {
        id: 'st-2',
        timestamp: 'Oct 25, 2024 • 11:15 AM',
        title: 'Payment Received',
        description: 'Full wire transfer verified by Finance',
        status: 'completed',
      },
      {
        id: 'st-3',
        timestamp: 'Current State',
        title: 'Fulfillment Processing',
        description: 'Main Hub (NY) warehouse picking order items',
        status: 'current',
      },
    ],
    comments: [
      {
        id: 'sc-1',
        author_name: 'Sarah Jenkins',
        time_ago: 'Yesterday',
        content: 'Customer requested palletized delivery to Gate B before 3 PM.',
      },
      {
        id: 'sc-2',
        author_name: 'System',
        time_ago: 'Yesterday',
        content: 'Inventory reservation confirmed across Main Hub warehouse.',
        is_system: true,
      },
    ],
  },
  'so-1002': {
    id: 'so-1002',
    order_number: 'SO-2024-1002',
    date: 'Oct 24, 2024',
    status: 'Confirmed',
    payment_status: 'Pending',
    fulfillment_status: 'Unfulfilled',
    customer_name: 'Apex Global Logistics',
    customer_email: 'ops@apexlogistics.eu',
    customer_phone: '+44 20 7946 0912',
    customer_company: 'Apex Global Logistics Ltd',
    billing_address: '14 Bishopsgate\nLondon EC2N 4BQ\nUnited Kingdom',
    shipping_address: 'Terminal 4 Distribution Center\nHeathrow Airport, Hounslow TW6 3XA\nUnited Kingdom',
    region: 'Europe',
    sales_rep: {
      name: 'Amit Patel',
      email: 'amit.patel@apnaerp.com',
      avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=50&auto=format&fit=crop&q=80',
      designation: 'Technical Account Lead',
    },
    expected_delivery: 'Nov 05, 2024',
    payment_terms: 'Net 45',
    shipping_carrier: 'DHL International Air',
    tracking_number: 'DHL-992014-EU',
    items: [
      {
        id: 'item-s20',
        item_name: 'Enterprise Server Racks 42U',
        description: 'Heavy duty standard rack cabinet with PDU',
        sku: 'HW-SR-42U',
        quantity: 16,
        unit_price: 1850.0,
        formatted_unit_price: '$1,850.00',
        tax_rate: 10,
        subtotal: 29600.0,
        formatted_subtotal: '$29,600.00',
      },
      {
        id: 'item-s21',
        item_name: 'Managed 48-Port PoE Switch',
        description: 'Layer 3 enterprise gigabit switch',
        sku: 'NT-SW-48M',
        quantity: 2,
        unit_price: 1600.0,
        formatted_unit_price: '$1,600.00',
        tax_rate: 10,
        subtotal: 3200.0,
        formatted_subtotal: '$3,200.00',
      },
    ],
    subtotal: 32800.0,
    formatted_subtotal: '$32,800.00',
    tax_amount: 3280.0,
    formatted_tax: '$3,280.00',
    shipping_amount: 750.0,
    formatted_shipping: '$750.00',
    discount_amount: 4030.0,
    formatted_discount: '-$4,030.00',
    total_amount: 32800.0,
    formatted_total: '$32,800.00',
    timeline: [
      {
        id: 'st-10',
        timestamp: 'Oct 24, 2024 • 02:00 PM',
        title: 'Order Confirmed',
        description: 'Customer Purchase Order verified against contract',
        user_name: 'Amit Patel',
        user_avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=50&auto=format&fit=crop&q=80',
        status: 'completed',
      },
      {
        id: 'st-11',
        timestamp: 'Current State',
        title: 'Awaiting Invoice Payment',
        description: 'Invoice #INV-2024-8802 dispatched to accounting',
        status: 'current',
      },
    ],
    comments: [
      {
        id: 'sc-10',
        author_name: 'Amit Patel',
        time_ago: '2 days ago',
        content: 'Client requested customs clearance documents pre-filled for UK arrival.',
      },
    ],
  },
};

export const salesService = {
  getSalesOrders: async (
    filters?: SalesOrderFilters
  ): Promise<{ items: SalesOrderListItem[]; total: number; metrics: SalesMetrics }> => {
    try {
      const response = await api.get('/api/v1/sales/orders', { params: filters });
      if (response.data && typeof response.data === 'object' && Array.isArray(response.data.items)) {
        return response.data;
      }
      return filterMockSalesOrders(filters);
    } catch {
      return filterMockSalesOrders(filters);
    }
  },

  getSalesOrderById: async (id: string): Promise<SalesOrderDetail | null> => {
    try {
      const response = await api.get(`/api/v1/sales/orders/${id}`);
      if (response.data && typeof response.data === 'object' && response.data.id) {
        return response.data;
      }
      return getMockSalesDetailById(id);
    } catch {
      return getMockSalesDetailById(id);
    }
  },

  createSalesOrder: async (orderData: {
    customer_name: string;
    region: string;
    amount: number;
    expected_delivery: string;
    sales_rep_name?: string;
  }): Promise<SalesOrderListItem> => {
    const newId = `so-${Date.now()}`;
    const newOrderNum = `SO-2024-${Math.floor(1060 + Math.random() * 900)}`;
    const initials = orderData.customer_name
      .split(' ')
      .map((w) => w[0])
      .slice(0, 2)
      .join('')
      .toUpperCase() || 'SO';

    const newListItem: SalesOrderListItem = {
      id: newId,
      order_number: newOrderNum,
      date: 'Today',
      customer_name: orderData.customer_name,
      customer_initials: initials,
      region: orderData.region,
      amount: orderData.amount,
      formatted_amount: `$${orderData.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      status: 'Confirmed',
      payment_status: 'Pending',
      fulfillment_status: 'Processing',
      sales_rep_name: orderData.sales_rep_name || 'ERP Admin',
      sales_rep_avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80',
      items_count: 1,
      expected_delivery: orderData.expected_delivery || 'Nov 15, 2024',
    };

    MOCK_SALES_ORDERS_LIST.unshift(newListItem);

    const newDetail: SalesOrderDetail = {
      id: newId,
      order_number: newOrderNum,
      date: 'Today',
      status: 'Confirmed',
      payment_status: 'Pending',
      fulfillment_status: 'Processing',
      customer_name: orderData.customer_name,
      customer_email: `contact@${orderData.customer_name.toLowerCase().replace(/[^a-z]/g, '')}.com`,
      customer_phone: '+1 (555) 000-1234',
      customer_company: orderData.customer_name,
      billing_address: `Headquarters Building\n${orderData.region}`,
      shipping_address: `Primary Receiving Depot\n${orderData.region}`,
      region: orderData.region,
      sales_rep: {
        name: orderData.sales_rep_name || 'ERP Admin',
        email: 'admin@apnaerp.com',
        avatar_url: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80',
        designation: 'Enterprise Account Representative',
      },
      expected_delivery: orderData.expected_delivery || 'Nov 15, 2024',
      payment_terms: 'Net 30',
      shipping_carrier: 'Standard Freight Logistics',
      tracking_number: `TRK-${Date.now().toString().slice(-8)}`,
      items: [
        {
          id: `item-${Date.now()}`,
          item_name: 'Custom Order Package',
          description: 'Enterprise merchandise and operational fulfillment',
          sku: 'PKG-ENT-001',
          quantity: 1,
          unit_price: orderData.amount,
          formatted_unit_price: `$${orderData.amount.toFixed(2)}`,
          tax_rate: 8,
          subtotal: orderData.amount,
          formatted_subtotal: `$${orderData.amount.toFixed(2)}`,
        },
      ],
      subtotal: orderData.amount,
      formatted_subtotal: `$${orderData.amount.toFixed(2)}`,
      tax_amount: orderData.amount * 0.08,
      formatted_tax: `$${(orderData.amount * 0.08).toFixed(2)}`,
      shipping_amount: 150.0,
      formatted_shipping: '$150.00',
      discount_amount: (orderData.amount * 0.08) + 150,
      formatted_discount: `-$${((orderData.amount * 0.08) + 150).toFixed(2)}`,
      total_amount: orderData.amount,
      formatted_total: `$${orderData.amount.toFixed(2)}`,
      timeline: [
        {
          id: `st-${Date.now()}`,
          timestamp: 'Just now',
          title: 'Order Created & Submitted',
          description: `Logged by ${orderData.sales_rep_name || 'ERP Admin'}`,
          status: 'completed',
        },
        {
          id: `st-${Date.now()}-2`,
          timestamp: 'Current State',
          title: 'Fulfillment In Progress',
          description: 'Ready for warehouse dispatch',
          status: 'current',
        },
      ],
      comments: [
        {
          id: `c-${Date.now()}`,
          author_name: orderData.sales_rep_name || 'ERP Admin',
          time_ago: 'Just now',
          content: 'Order created and queued for immediate warehouse allocation.',
        },
      ],
    };

    MOCK_SALES_DETAILS_MAP[newId] = newDetail;
    return newListItem;
  },

  updateOrderStatus: async (
    id: string,
    status: SalesOrderStatus,
    fulfillmentStatus?: SalesOrderDetail['fulfillment_status']
  ): Promise<SalesOrderDetail | null> => {
    try {
      const response = await api.put(`/api/v1/sales/orders/${id}/status`, { status, fulfillmentStatus });
      if (response.data && typeof response.data === 'object' && response.data.id) {
        return response.data;
      }
    } catch {
      // Continue local update
    }

    const detail = getMockSalesDetailById(id);
    if (!detail) return null;
    detail.status = status;
    if (fulfillmentStatus) detail.fulfillment_status = fulfillmentStatus;

    // Also update in list
    const cleanId = id.trim().toLowerCase();
    const foundListItem = MOCK_SALES_ORDERS_LIST.find(
      (o) => o.id.toLowerCase() === cleanId || o.order_number.toLowerCase() === cleanId
    );
    if (foundListItem) {
      foundListItem.status = status;
      if (fulfillmentStatus) foundListItem.fulfillment_status = fulfillmentStatus;
    }

    MOCK_SALES_DETAILS_MAP[detail.id] = detail;
    return detail;
  },

  addComment: async (id: string, content: string): Promise<SalesOrderDetail | null> => {
    const detail = getMockSalesDetailById(id);
    if (!detail) return null;
    const newComment = {
      id: `c-${Date.now()}`,
      author_name: 'ERP Admin',
      time_ago: 'Just now',
      content,
      is_system: false,
    };
    detail.comments.unshift(newComment);
    MOCK_SALES_DETAILS_MAP[detail.id] = detail;
    return detail;
  },
};

function filterMockSalesOrders(filters?: SalesOrderFilters) {
  let items = [...MOCK_SALES_ORDERS_LIST];

  if (filters?.search) {
    const q = filters.search.toLowerCase();
    items = items.filter(
      (o) =>
        o.order_number.toLowerCase().includes(q) ||
        o.customer_name.toLowerCase().includes(q) ||
        o.sales_rep_name.toLowerCase().includes(q)
    );
  }

  if (filters?.customer && filters.customer !== 'All Customers' && filters.customer !== 'All') {
    items = items.filter((o) => o.customer_name.toLowerCase() === filters.customer!.toLowerCase());
  }

  if (filters?.region && filters.region !== 'All Regions' && filters.region !== 'All') {
    items = items.filter((o) => o.region.toLowerCase() === filters.region!.toLowerCase());
  }

  if (filters?.fulfillment && filters.fulfillment !== 'All Fulfillment' && filters.fulfillment !== 'All') {
    items = items.filter((o) => o.fulfillment_status.toLowerCase() === filters.fulfillment!.toLowerCase());
  }

  if (filters?.paymentStatus && filters.paymentStatus !== 'All Payment' && filters.paymentStatus !== 'All') {
    items = items.filter((o) => o.payment_status.toLowerCase() === filters.paymentStatus!.toLowerCase());
  }

  if (filters?.status && filters.status !== 'All Statuses' && filters.status !== 'All') {
    items = items.filter((o) => o.status.toLowerCase() === filters.status!.toLowerCase());
  }

  const totalRevenue = items.reduce((sum, o) => sum + o.amount, 0);
  const pendingCount = items.filter((o) => o.fulfillment_status !== 'Delivered' && o.fulfillment_status !== 'Cancelled').length;
  const avgOrder = items.length > 0 ? totalRevenue / items.length : 0;

  const metrics: SalesMetrics = {
    total_orders_count: items.length,
    total_revenue_formatted: `$${(totalRevenue / 1000).toFixed(1)}k`,
    pending_fulfillment_count: pendingCount,
    average_order_value_formatted: `$${avgOrder.toFixed(0)}`,
  };

  return {
    items,
    total: items.length,
    metrics,
  };
}

function getMockSalesDetailById(id: string): SalesOrderDetail | null {
  if (!id) return null;
  const cleanId = id.trim().toLowerCase();

  // Direct match in map
  for (const [key, detail] of Object.entries(MOCK_SALES_DETAILS_MAP)) {
    if (key.toLowerCase() === cleanId || detail.order_number.toLowerCase() === cleanId) {
      return detail;
    }
  }

  const foundInList = MOCK_SALES_ORDERS_LIST.find(
    (o) => o.id.toLowerCase() === cleanId || o.order_number.toLowerCase() === cleanId
  );
  if (foundInList) {
    const detail: SalesOrderDetail = {
      id: foundInList.id,
      order_number: foundInList.order_number,
      date: foundInList.date,
      status: foundInList.status,
      payment_status: foundInList.payment_status,
      fulfillment_status: foundInList.fulfillment_status,
      customer_name: foundInList.customer_name,
      customer_email: `contact@${foundInList.customer_name.toLowerCase().replace(/[^a-z]/g, '')}.com`,
      customer_phone: '+1 (555) 432-9876',
      customer_company: foundInList.customer_name,
      billing_address: `Corporate Office Suite\n${foundInList.region}`,
      shipping_address: `Central Logistics Warehouse\n${foundInList.region}`,
      region: foundInList.region,
      sales_rep: {
        name: foundInList.sales_rep_name,
        email: `${foundInList.sales_rep_name.toLowerCase().replace(/[^a-z]/g, '.')}@apnaerp.com`,
        avatar_url: foundInList.sales_rep_avatar || 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=50&auto=format&fit=crop&q=80',
        designation: 'Enterprise Account Representative',
      },
      expected_delivery: foundInList.expected_delivery,
      payment_terms: 'Net 30',
      shipping_carrier: 'Global Freight Courier',
      tracking_number: `TRK-${foundInList.order_number.replace(/[^0-9]/g, '')}`,
      items: [
        {
          id: `item-${foundInList.id}-1`,
          item_name: `Enterprise Solution Bundle (${foundInList.customer_name})`,
          description: 'Full equipment provisioning and deployment services',
          sku: 'SOL-ENT-900',
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
      shipping_amount: 250.0,
      formatted_shipping: '$250.00',
      discount_amount: (foundInList.amount * 0.08) + 250,
      formatted_discount: `-$${((foundInList.amount * 0.08) + 250).toFixed(2)}`,
      total_amount: foundInList.amount,
      formatted_total: foundInList.formatted_amount,
      timeline: [
        {
          id: 'st-dyn-1',
          timestamp: `${foundInList.date} • 10:00 AM`,
          title: 'Order Confirmed',
          description: `Processed by ${foundInList.sales_rep_name}`,
          status: 'completed',
        },
        {
          id: 'st-dyn-2',
          timestamp: 'Current State',
          title: `Status: ${foundInList.status}`,
          description: `Fulfillment: ${foundInList.fulfillment_status}`,
          status: 'current',
        },
      ],
      comments: [
        {
          id: 'sc-dyn-1',
          author_name: foundInList.sales_rep_name,
          time_ago: 'Recently',
          content: `Account setup initiated for ${foundInList.customer_name}.`,
        },
      ],
    };
    MOCK_SALES_DETAILS_MAP[foundInList.id] = detail;
    return detail;
  }

  // Return null if not found
  return null;
}
