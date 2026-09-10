import React, { useState, useEffect } from 'react';
import {
  Target,
  Plus,
  RefreshCw,
  Search,
  Building2,
  Mail,
  Phone,
  DollarSign,
  ArrowRightCircle,
  FileText,
  MessageSquare,
  CheckCircle2,
  Filter,
} from 'lucide-react';
import { crmService } from '../../services/crmService';
import { LeadItem } from '../../types/crm';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

export const CrmLeadsPage: React.FC = () => {
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('All');

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);
  const [selectedLead, setSelectedLead] = useState<LeadItem | null>(null);
  const [noteText, setNoteText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [formData, setFormData] = useState<Partial<LeadItem>>({
    first_name: '',
    last_name: '',
    company_name: '',
    title: '',
    email: '',
    phone: '',
    source: 'Website',
    status: 'New',
    estimated_value: 10000,
    notes: '',
  });

  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadLeads();
  }, [selectedStatus]);

  const loadLeads = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await crmService.getLeads({
        status: selectedStatus !== 'All' ? selectedStatus : undefined,
      });
      setLeads(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load CRM leads');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.first_name || !formData.last_name) {
      toastError('First and last name are required');
      return;
    }
    setIsSubmitting(true);
    try {
      await crmService.createLead(formData);
      success('Lead Created', `${formData.first_name} ${formData.last_name} added to pipeline.`);
      setIsAddModalOpen(false);
      setFormData({
        first_name: '',
        last_name: '',
        company_name: '',
        title: '',
        email: '',
        phone: '',
        source: 'Website',
        status: 'New',
        estimated_value: 10000,
        notes: '',
      });
      loadLeads();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to create lead');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConvertLead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await crmService.convertLead(id);
      success('Lead Converted', 'Lead converted into an active Customer & Opportunity.');
      loadLeads();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to convert lead');
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLead || !noteText.trim()) return;
    setIsSubmitting(true);
    try {
      await crmService.addLeadNote(selectedLead.id, noteText.trim());
      success('Note Logged', 'Lead activity note appended.');
      setIsNoteModalOpen(false);
      setNoteText('');
      loadLeads();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to add note');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filtered = leads.filter((l) => {
    const name = `${l.first_name || ''} ${l.last_name || ''}`.toLowerCase();
    const company = (l.company_name || '').toLowerCase();
    const email = (l.email || '').toLowerCase();
    const q = searchQuery.toLowerCase();
    return name.includes(q) || company.includes(q) || email.includes(q);
  });

  const totalEstValue = leads.reduce((acc, l) => acc + (l.estimated_value || 0), 0);
  const convertedCount = leads.filter((l) => l.status === 'Converted').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">CRM Leads & Prospects</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Capture prospective accounts, qualify deal size, record touchpoints, and convert to sales
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadLeads}>
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={<Plus className="w-4 h-4" />}
            onClick={() => setIsAddModalOpen(true)}
          >
            Add Lead
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Total Leads"
          value={leads.length}
          icon={<Target className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Inbound inquiries"
        />
        <KpiCard
          title="Pipeline Est. Value"
          value={`$${totalEstValue.toLocaleString()}`}
          icon={<DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Potential deal volume"
        />
        <KpiCard
          title="Converted Leads"
          value={convertedCount}
          icon={<CheckCircle2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Transformed into clients"
        />
        <KpiCard
          title="Conversion Rate"
          value={`${leads.length > 0 ? ((convertedCount / leads.length) * 100).toFixed(1) : 0}%`}
          icon={<ArrowRightCircle className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Prospect win ratio"
        />
      </div>

      {/* Search & Filter */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search lead by name, company, email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="All">All Stages</option>
            <option value="New">New</option>
            <option value="Contacted">Contacted</option>
            <option value="Qualified">Qualified</option>
            <option value="Proposal">Proposal</option>
            <option value="Negotiation">Negotiation</option>
            <option value="Converted">Converted</option>
            <option value="Lost">Lost</option>
          </select>
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8">
            <LoadingState message="Loading CRM leads..." />
          </div>
        ) : error ? (
          <div className="p-8">
            <ErrorState title="Failed to load leads" message={error} onRetry={loadLeads} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No CRM leads found"
              description="Capture new inbound prospects to build your sales funnel."
              action={
                <Button
                  variant="primary"
                  icon={<Plus className="w-4 h-4" />}
                  onClick={() => setIsAddModalOpen(true)}
                >
                  Add Lead
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
              <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-4">Contact Name</th>
                  <th className="px-6 py-4">Company</th>
                  <th className="px-6 py-4">Contact Info</th>
                  <th className="px-6 py-4">Source</th>
                  <th className="px-6 py-4 text-right">Est. Value</th>
                  <th className="px-6 py-4">Stage</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {filtered.map((l) => (
                  <tr key={l.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-gray-900 dark:text-white">
                        {l.first_name} {l.last_name}
                      </div>
                      {l.title && <div className="text-xs text-gray-400">{l.title}</div>}
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-900 dark:text-white">
                      {l.company_name || 'Individual'}
                    </td>
                    <td className="px-6 py-4 space-y-0.5">
                      {l.email && (
                        <div className="flex items-center gap-1.5 text-xs text-gray-500">
                          <Mail className="w-3.5 h-3.5 text-gray-400" /> {l.email}
                        </div>
                      )}
                      {l.phone && (
                        <div className="flex items-center gap-1.5 text-xs text-gray-500">
                          <Phone className="w-3.5 h-3.5 text-gray-400" /> {l.phone}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                        {l.source || 'Website'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      ${Number(l.estimated_value || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge
                        status={l.status}
                        variant={
                          l.status === 'Converted'
                            ? 'success'
                            : l.status === 'Qualified' || l.status === 'Proposal'
                            ? 'info'
                            : l.status === 'Lost'
                            ? 'error'
                            : 'default'
                        }
                      />
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          title="Add Activity Note"
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                          onClick={() => {
                            setSelectedLead(l);
                            setIsNoteModalOpen(true);
                          }}
                        >
                          <MessageSquare className="w-4 h-4" />
                        </button>
                        {l.status !== 'Converted' && (
                          <Button
                            size="sm"
                            variant="primary"
                            icon={<ArrowRightCircle className="w-3.5 h-3.5" />}
                            onClick={(e) => handleConvertLead(l.id, e)}
                          >
                            Convert
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Add Lead */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Capture New CRM Lead"
        size="lg"
      >
        <form onSubmit={handleCreateLead} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                First Name *
              </label>
              <input
                type="text"
                required
                placeholder="John"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Last Name *
              </label>
              <input
                type="text"
                required
                placeholder="Doe"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Company Name
              </label>
              <input
                type="text"
                placeholder="Acme Corp"
                value={formData.company_name}
                onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Job Title
              </label>
              <input
                type="text"
                placeholder="VP of Procurement"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Email Address
              </label>
              <input
                type="email"
                placeholder="john@acme.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Phone Number
              </label>
              <input
                type="tel"
                placeholder="+1 555-0100"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Lead Source
              </label>
              <select
                value={formData.source}
                onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                <option value="Website">Website Inbound</option>
                <option value="Referral">Referral</option>
                <option value="Trade Show">Trade Show / Conference</option>
                <option value="Cold Outreach">Cold Outreach</option>
                <option value="Partner">Partner Channel</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Estimated Deal Value ($)
              </label>
              <input
                type="number"
                min="0"
                value={formData.estimated_value}
                onChange={(e) => setFormData({ ...formData, estimated_value: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Initial Notes / Inquiry Details
            </label>
            <textarea
              rows={2}
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Client requirements, budget range, timeline..."
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsAddModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Create Lead
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Add Note */}
      {selectedLead && (
        <Modal
          isOpen={isNoteModalOpen}
          onClose={() => setIsNoteModalOpen(false)}
          title={`Log Note for ${selectedLead.first_name} ${selectedLead.last_name}`}
        >
          <form onSubmit={handleAddNote} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Note Content *
              </label>
              <textarea
                rows={4}
                required
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Call summary, follow-up schedule, meeting notes..."
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button type="button" variant="secondary" onClick={() => setIsNoteModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" loading={isSubmitting}>
                Save Note
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
