import { api } from './api';
import { LeadItem, OpportunityItem, CrmActivityItem } from '../types/crm';

export const crmService = {
  // Leads
  async getLeads(params?: { search?: string; status?: string }): Promise<LeadItem[]> {
    const response = await api.get('/api/v1/crm/leads', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createLead(data: Partial<LeadItem>): Promise<LeadItem> {
    const response = await api.post('/api/v1/crm/leads', data);
    return response.data;
  },

  async updateLead(id: string, data: Partial<LeadItem>): Promise<LeadItem> {
    const response = await api.put(`/api/v1/crm/leads/${id}`, data);
    return response.data;
  },

  async convertLead(id: string): Promise<any> {
    const response = await api.post(`/api/v1/crm/leads/${id}/convert`, {});
    return response.data;
  },

  async addLeadNote(id: string, noteText: string): Promise<any> {
    const response = await api.post(`/api/v1/crm/leads/${id}/notes`, { note_text: noteText });
    return response.data;
  },

  // Opportunities
  async getOpportunities(params?: { stage?: string }): Promise<OpportunityItem[]> {
    const response = await api.get('/api/v1/crm/opportunities', { params });
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createOpportunity(data: Partial<OpportunityItem>): Promise<OpportunityItem> {
    const response = await api.post('/api/v1/crm/opportunities', data);
    return response.data;
  },

  async updateOpportunityStage(id: string, stage: string): Promise<OpportunityItem> {
    const response = await api.post(`/api/v1/crm/opportunities/${id}/stage`, { stage });
    return response.data;
  },

  // Activities
  async getActivities(): Promise<CrmActivityItem[]> {
    const response = await api.get('/api/v1/crm/activities');
    if (Array.isArray(response.data)) return response.data;
    if (response.data?.items) return response.data.items;
    return [];
  },

  async createActivity(data: Partial<CrmActivityItem>): Promise<CrmActivityItem> {
    const response = await api.post('/api/v1/crm/activities', data);
    return response.data;
  },

  async completeActivity(id: string): Promise<CrmActivityItem> {
    const response = await api.post(`/api/v1/crm/activities/${id}/complete`);
    return response.data;
  },
};
