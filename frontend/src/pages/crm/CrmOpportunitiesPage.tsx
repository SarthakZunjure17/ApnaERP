import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Plus,
  RefreshCw,
  Search,
  Building2,
  DollarSign,
  Calendar,
  CheckCircle2,
  XCircle,
  Activity,
  Layers,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { crmService } from '../../services/crmService';
import { salesService } from '../../services/salesService';
import { OpportunityItem, CrmActivityItem } from '../../types/crm';
import { CustomerItem } from '../../types/sales';
import { StatusBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { Button } from '../../components/common/Button';
import { LoadingState } from '../../components/common/LoadingState';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { KpiCard } from '../../components/common/KpiCard';
import { useToast } from '../../context/ToastContext';

type StageType = 'Prospecting' | 'Qualification' | 'Proposal' | 'Negotiation' | 'Closed Won' | 'Closed Lost';
const STAGES: StageType[] = ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost'];

export const CrmOpportunitiesPage: React.FC = () => {
  const [opportunities, setOpportunities] = useState<OpportunityItem[]>([]);
  const [activities, setActivities] = useState<CrmActivityItem[]>([]);
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isAddOppModalOpen, setIsAddOppModalOpen] = useState(false);
  const [isAddActivityModalOpen, setIsAddActivityModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // View state
  const [activeTab, setActiveTab] = useState<'pipeline' | 'activities'>('pipeline');
  const [searchQuery, setSearchQuery] = useState('');

  // Form State
  const [oppForm, setOppForm] = useState({
    name: '',
    customer_id: '',
    deal_value: 25000,
    probability: 50,
    stage: 'Prospecting' as StageType,
    expected_close_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
  });

  const [actForm, setActForm] = useState({
    subject: '',
    activity_type: 'Call' as 'Call' | 'Meeting' | 'Email' | 'Note' | 'Task',
    due_date: new Date().toISOString().split('T')[0],
    description: '',
  });

  const { success, error: toastError } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [oppList, actList, custList] = await Promise.all([
        crmService.getOpportunities(),
        crmService.getActivities(),
        salesService.getCustomers(),
      ]);
      setOpportunities(oppList);
      setActivities(actList);
      setCustomers(custList);
      if (custList.length > 0 && !oppForm.customer_id) {
        setOppForm((prev) => ({ ...prev, customer_id: custList[0].id }));
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load opportunities');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateOpportunity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!oppForm.name) {
      toastError('Opportunity name is required');
      return;
    }
    setIsSubmitting(true);
    try {
      await crmService.createOpportunity(oppForm);
      success('Opportunity Created', `${oppForm.name} added to sales pipeline.`);
      setIsAddOppModalOpen(false);
      loadData();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to create opportunity');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStageChange = async (id: string, newStage: string) => {
    try {
      await crmService.updateOpportunityStage(id, newStage);
      success('Stage Updated', `Opportunity moved to ${newStage}.`);
      loadData();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to update stage');
    }
  };

  const handleCreateActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!actForm.subject) return;
    setIsSubmitting(true);
    try {
      await crmService.createActivity({
        ...actForm,
        status: 'Pending',
      });
      success('Activity Logged', 'CRM task/activity recorded.');
      setIsAddActivityModalOpen(false);
      setActForm({
        subject: '',
        activity_type: 'Call',
        due_date: new Date().toISOString().split('T')[0],
        description: '',
      });
      loadData();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to record activity');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCompleteActivity = async (id: string) => {
    try {
      await crmService.completeActivity(id);
      success('Activity Completed', 'Task marked finished.');
      loadData();
    } catch (err: any) {
      toastError(err.response?.data?.detail || 'Failed to complete activity');
    }
  };

  const totalPipelineValue = opportunities.reduce((acc, o) => acc + (Number(o.deal_value) || 0), 0);
  const wonCount = opportunities.filter((o) => o.stage === 'Closed Won').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Deals & Opportunities Pipeline</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Track qualified deal velocity, stage progression, probability forecasting, and customer activities
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={<RefreshCw className="w-4 h-4" />} onClick={loadData}>
            Refresh
          </Button>
          {activeTab === 'pipeline' && (
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setIsAddOppModalOpen(true)}
            >
              New Opportunity
            </Button>
          )}
          {activeTab === 'activities' && (
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setIsAddActivityModalOpen(true)}
            >
              Log Activity
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiCard
          title="Active Opportunities"
          value={opportunities.length}
          icon={<TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
          description="Pipeline deals in motion"
        />
        <KpiCard
          title="Total Pipeline Value"
          value={`$${totalPipelineValue.toLocaleString()}`}
          icon={<DollarSign className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          description="Cumulative deal forecast"
        />
        <KpiCard
          title="Deals Won"
          value={wonCount}
          icon={<CheckCircle2 className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
          description="Closed-won opportunities"
        />
        <KpiCard
          title="Scheduled Activities"
          value={activities.filter((a) => a.status === 'Pending').length}
          icon={<Activity className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
          description="Pending customer tasks"
        />
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 space-x-2">
        <button
          onClick={() => setActiveTab('pipeline')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'pipeline'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Layers className="w-4 h-4" /> Pipeline Stages
        </button>
        <button
          onClick={() => setActiveTab('activities')}
          className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2 ${
            activeTab === 'activities'
              ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 border-t-2 border-blue-600 dark:border-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
          }`}
        >
          <Activity className="w-4 h-4" /> CRM Activities ({activities.length})
        </button>
      </div>

      {/* Main Content Area */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden p-6">
        {isLoading ? (
          <LoadingState message="Loading CRM pipeline..." />
        ) : error ? (
          <ErrorState title="Failed to load pipeline" message={error} onRetry={loadData} />
        ) : (
          <>
            {/* Tab: Pipeline Stages View */}
            {activeTab === 'pipeline' && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                {STAGES.map((stage) => {
                  const stageDeals = opportunities.filter((o) => o.stage === stage);
                  const stageSum = stageDeals.reduce((acc, d) => acc + (Number(d.deal_value) || 0), 0);

                  return (
                    <div
                      key={stage}
                      className="bg-gray-50 dark:bg-gray-700/30 rounded-xl p-3 border border-gray-200 dark:border-gray-700 flex flex-col h-[520px]"
                    >
                      <div className="flex items-center justify-between pb-2 border-b border-gray-200 dark:border-gray-600 mb-3">
                        <span className="font-semibold text-xs uppercase text-gray-700 dark:text-gray-300">
                          {stage}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-bold">
                          {stageDeals.length}
                        </span>
                      </div>

                      <div className="text-[11px] font-mono text-gray-500 dark:text-gray-400 mb-3">
                        Total: ${stageSum.toLocaleString()}
                      </div>

                      <div className="space-y-3 flex-1 overflow-y-auto pr-1">
                        {stageDeals.length === 0 ? (
                          <div className="text-center text-xs text-gray-400 py-8">No deals</div>
                        ) : (
                          stageDeals.map((deal) => (
                            <div
                              key={deal.id}
                              className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:border-blue-500 transition-all space-y-2"
                            >
                              <div className="font-semibold text-sm text-gray-900 dark:text-white leading-tight">
                                {deal.name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                                <Building2 className="w-3 h-3" /> {deal.customer_name || 'Client'}
                              </div>
                              <div className="flex items-center justify-between pt-1 border-t border-gray-100 dark:border-gray-700">
                                <span className="font-mono font-bold text-xs text-emerald-600 dark:text-emerald-400">
                                  ${Number(deal.deal_value || 0).toLocaleString()}
                                </span>
                                <span className="text-[10px] text-gray-400 font-mono">{deal.probability || 50}%</span>
                              </div>

                              {/* Quick Stage Progression */}
                              <div className="pt-1">
                                <select
                                  value={deal.stage}
                                  onChange={(e) => handleStageChange(deal.id, e.target.value)}
                                  className="w-full text-[10px] py-1 px-1.5 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                >
                                  {STAGES.map((s) => (
                                    <option key={s} value={s}>
                                      Move to {s}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Tab: Activities View */}
            {activeTab === 'activities' && (
              <div className="space-y-4">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                    <thead className="bg-gray-50 dark:bg-gray-700/50 text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                      <tr>
                        <th className="px-6 py-4">Activity Type</th>
                        <th className="px-6 py-4">Subject</th>
                        <th className="px-6 py-4">Due Date</th>
                        <th className="px-6 py-4">Status</th>
                        <th className="px-6 py-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {activities.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="px-6 py-8 text-center text-gray-400">
                            No CRM activities logged. Click "Log Activity" to create a task or touchpoint.
                          </td>
                        </tr>
                      ) : (
                        activities.map((a) => (
                          <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                            <td className="px-6 py-4">
                              <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                                {a.activity_type}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <div className="font-semibold text-gray-900 dark:text-white">{a.subject}</div>
                              {a.description && <div className="text-xs text-gray-400">{a.description}</div>}
                            </td>
                            <td className="px-6 py-4 text-xs text-gray-500">{a.due_date || '-'}</td>
                            <td className="px-6 py-4">
                              <StatusBadge
                                status={a.status}
                                variant={a.status === 'Completed' ? 'success' : 'warning'}
                              />
                            </td>
                            <td className="px-6 py-4 text-right">
                              {a.status !== 'Completed' && (
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  icon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
                                  onClick={() => handleCompleteActivity(a.id)}
                                >
                                  Complete
                                </Button>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modal: New Opportunity */}
      <Modal
        isOpen={isAddOppModalOpen}
        onClose={() => setIsAddOppModalOpen(false)}
        title="Create Opportunity Deal"
        size="md"
      >
        <form onSubmit={handleCreateOpportunity} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Deal Title / Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Enterprise Cloud ERP Expansion"
              value={oppForm.name}
              onChange={(e) => setOppForm({ ...oppForm, name: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Customer Account
            </label>
            <select
              value={oppForm.customer_id}
              onChange={(e) => setOppForm({ ...oppForm, customer_id: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            >
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Deal Value ($) *
              </label>
              <input
                type="number"
                min="0"
                required
                value={oppForm.deal_value}
                onChange={(e) => setOppForm({ ...oppForm, deal_value: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Win Probability (%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={oppForm.probability}
                onChange={(e) => setOppForm({ ...oppForm, probability: parseInt(e.target.value, 10) || 50 })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Initial Stage
              </label>
              <select
                value={oppForm.stage}
                onChange={(e) => setOppForm({ ...oppForm, stage: e.target.value as StageType })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                {STAGES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
                Expected Close Date
              </label>
              <input
                type="date"
                value={oppForm.expected_close_date}
                onChange={(e) => setOppForm({ ...oppForm, expected_close_date: e.target.value })}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsAddOppModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Create Deal
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: New Activity */}
      <Modal
        isOpen={isAddActivityModalOpen}
        onClose={() => setIsAddActivityModalOpen(false)}
        title="Log CRM Activity / Task"
        size="md"
      >
        <form onSubmit={handleCreateActivity} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Activity Type *
            </label>
            <select
              value={actForm.activity_type}
              onChange={(e) =>
                setActForm({
                  ...actForm,
                  activity_type: e.target.value as 'Call' | 'Meeting' | 'Email' | 'Note' | 'Task',
                })
              }
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            >
              <option value="Call">Phone Call</option>
              <option value="Meeting">Client Meeting</option>
              <option value="Email">Email Communication</option>
              <option value="Task">Action Item / Task</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Subject / Action *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Follow-up demo call with CTO"
              value={actForm.subject}
              onChange={(e) => setActForm({ ...actForm, subject: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Due Date
            </label>
            <input
              type="date"
              value={actForm.due_date}
              onChange={(e) => setActForm({ ...actForm, due_date: e.target.value })}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-gray-700 dark:text-gray-300 mb-1">
              Description / Notes
            </label>
            <textarea
              rows={3}
              value={actForm.description}
              onChange={(e) => setActForm({ ...actForm, description: e.target.value })}
              placeholder="Agenda, discussion points..."
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsAddActivityModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Save Activity
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
