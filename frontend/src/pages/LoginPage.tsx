import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Boxes,
  AlertCircle,
  KeyRound,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Modal } from '../components/common/Modal';
import { Button } from '../components/common/Button';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();
  const { success, error: toastError } = useToast();

  const [email, setEmail] = useState('admin@apnaerp.com');
  const [password, setPassword] = useState('admin123');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isForgotModalOpen, setIsForgotModalOpen] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetSent, setResetSent] = useState(false);

  // If already logged in, redirect to dashboard or intended route
  React.useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email.trim()) {
      setErrorMessage('Please enter your email address or username.');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter your password.');
      return;
    }

    setIsLoading(true);
    try {
      await login({
        username_or_email: email.trim(),
        password,
        remember_me: rememberMe,
      });
      success('Welcome back!', 'Successfully signed in to ApnaERP.');
      const from = (location.state as any)?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    } catch (err: any) {
      const msg = err.message || 'Invalid credentials. Please check and try again.';
      setErrorMessage(msg);
      toastError('Authentication Failed', msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFillDemo = (userEmail: string, pass: string) => {
    setEmail(userEmail);
    setPassword(pass);
    setErrorMessage(null);
  };

  const handleForgotPassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetEmail.trim()) return;
    setResetSent(true);
  };

  return (
    <div className="min-h-screen bg-grid-pattern flex flex-col justify-center items-center px-4 py-12 select-none">
      {/* Main Login Card (Matching Screenshot 12) */}
      <div className="w-full max-w-[420px] bg-white dark:bg-slate-900 rounded-2xl shadow-modal border border-slate-200/90 dark:border-slate-800 p-8 relative animate-fade-in">
        {/* Brand Logo & Header */}
        <div className="flex flex-col items-center text-center mb-7">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center text-white shadow-md shadow-brand-500/20">
              <Boxes className="w-5 h-5" />
            </div>
            <span className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              Apna<span className="text-brand-600">ERP</span>
            </span>
          </div>

          <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
            Welcome back
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Sign in to your ApnaERP account
          </p>
        </div>

        {/* Error Alert Message */}
        {errorMessage && (
          <div className="mb-5 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 flex items-start gap-2.5 text-xs text-rose-700 dark:text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1">{errorMessage}</div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email Address Field */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1.5">
              Email Address
            </label>
            <div className="relative flex items-center">
              <Mail className="absolute left-3.5 w-4 h-4 text-slate-400 pointer-events-none" />
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                autoComplete="username"
                className="w-full pl-10 pr-3.5 py-2.5 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-600 transition-all"
              />
            </div>
          </div>

          {/* Password Field */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1.5">
              Password
            </label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3.5 w-4 h-4 text-slate-400 pointer-events-none" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="•••••"
                autoComplete="current-password"
                className="w-full pl-10 pr-10 py-2.5 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-600 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-3 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Remember me & Forgot password */}
          <div className="flex items-center justify-between pt-1">
            <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded text-brand-600 border-slate-300 focus:ring-brand-500"
              />
              <span>Remember me</span>
            </label>

            <button
              type="button"
              onClick={() => {
                setResetEmail(email);
                setResetSent(false);
                setIsForgotModalOpen(true);
              }}
              className="text-xs font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400 hover:underline cursor-pointer"
            >
              Forgot password?
            </button>
          </div>

          {/* Submit Sign In Button */}
          <div className="pt-2">
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isLoading}
              className="w-full py-2.5 font-semibold bg-brand-600 hover:bg-brand-700 text-white rounded-lg shadow-sm flex items-center justify-center gap-2"
            >
              <span>Sign In</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </form>

        {/* Quick Demo Credentials Assistant */}
        <div className="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800">
          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-2">
            <span className="font-semibold uppercase tracking-wider flex items-center gap-1">
              <KeyRound className="w-3 h-3 text-brand-500" />
              Quick Test Credentials
            </span>
            <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-0.5 font-medium">
              <ShieldCheck className="w-3 h-3" /> Ready
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleFillDemo('admin@apnaerp.com', 'admin123')}
              className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-brand-50 dark:hover:bg-brand-950/40 border border-slate-200/80 dark:border-slate-700 text-left transition-colors cursor-pointer group"
            >
              <span className="block text-[11px] font-bold text-slate-800 dark:text-slate-200 group-hover:text-brand-600">
                ERP Admin
              </span>
              <span className="block text-[10px] text-slate-400 truncate">
                admin@apnaerp.com
              </span>
            </button>

            <button
              type="button"
              onClick={() => handleFillDemo('sarah.j@apnaerp.com', 'password123')}
              className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 hover:bg-brand-50 dark:hover:bg-brand-950/40 border border-slate-200/80 dark:border-slate-700 text-left transition-colors cursor-pointer group"
            >
              <span className="block text-[11px] font-bold text-slate-800 dark:text-slate-200 group-hover:text-brand-600">
                Sarah Jenkins
              </span>
              <span className="block text-[10px] text-slate-400 truncate">
                sarah.j@apnaerp.com
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Footer Support Links (Matching Screenshot 12) */}
      <div className="mt-8 text-xs text-slate-500 dark:text-slate-400 flex items-center gap-4">
        <a href="#support" className="hover:text-slate-800 dark:hover:text-slate-200 transition-colors">
          Contact Support
        </a>
        <span>•</span>
        <a href="#privacy" className="hover:text-slate-800 dark:hover:text-slate-200 transition-colors">
          Privacy Policy
        </a>
      </div>

      {/* Forgot Password Modal */}
      <Modal
        isOpen={isForgotModalOpen}
        onClose={() => setIsForgotModalOpen(false)}
        title="Reset Your Password"
      >
        {resetSent ? (
          <div className="text-center py-4 space-y-3">
            <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 mx-auto flex items-center justify-center">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
              Password Reset Link Dispatched
            </h4>
            <p className="text-xs text-slate-500">
              We have sent recovery instructions to{' '}
              <strong className="text-slate-700 dark:text-slate-300">{resetEmail}</strong>.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsForgotModalOpen(false)}
              className="mt-4"
            >
              Close
            </Button>
          </div>
        ) : (
          <form onSubmit={handleForgotPassword} className="space-y-4">
            <p className="text-xs text-slate-500">
              Enter your registered corporate email address and we'll send you a secure verification link to reset your account credentials.
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-200 mb-1">
                Corporate Email
              </label>
              <input
                type="email"
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                placeholder="name@company.com"
                required
                className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-brand-500"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsForgotModalOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm">
                Send Reset Link
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
};
