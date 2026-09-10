export interface LeadItem {
  id: string;
  lead_code?: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  company_name?: string;
  title?: string;
  email?: string;
  phone?: string;
  source?: string;
  status: 'New' | 'Contacted' | 'Qualified' | 'Proposal' | 'Negotiation' | 'Converted' | 'Lost';
  estimated_value?: number;
  assigned_to_user_id?: string;
  assigned_to_name?: string;
  created_at: string;
  notes?: string;
}

export interface OpportunityItem {
  id: string;
  opportunity_code?: string;
  name: string;
  customer_id?: string;
  customer_name?: string;
  lead_id?: string;
  stage: 'Prospecting' | 'Qualification' | 'Proposal' | 'Negotiation' | 'Closed Won' | 'Closed Lost';
  deal_value: number;
  probability: number;
  expected_close_date?: string;
  assigned_to_user_id?: string;
  assigned_to_name?: string;
  created_at: string;
}

export interface CrmActivityItem {
  id: string;
  activity_type: 'Call' | 'Meeting' | 'Email' | 'Note' | 'Task';
  subject: string;
  description?: string;
  due_date?: string;
  status: 'Pending' | 'Completed' | 'Cancelled';
  lead_id?: string;
  opportunity_id?: string;
  customer_id?: string;
  created_at: string;
}
