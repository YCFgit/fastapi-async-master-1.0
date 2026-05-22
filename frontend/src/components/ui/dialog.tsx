// frontend/src/components/ui/dialog.tsx
import React from 'react';

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

interface DialogContentProps {
  children: React.ReactNode;
  className?: string;
}

interface DialogHeaderProps {
  children: React.ReactNode;
}

interface DialogTitleProps {
  children: React.ReactNode;
}

interface DialogDescriptionProps {
  children: React.ReactNode;
}

interface DialogFooterProps {
  children: React.ReactNode;
}

export const Dialog: React.FC<DialogProps> = ({ open, onOpenChange, children }) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0"
        style={{ background: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(4px)' }}
        onClick={() => onOpenChange(false)}
      />
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};

export const DialogContent: React.FC<DialogContentProps> = ({ children, className = '' }) => {
  return (
    <div
      className={`rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 ${className}`}
      style={{
        background: 'linear-gradient(135deg, var(--bg-elevated), var(--bg-secondary))',
        border: '1px solid var(--border-default)',
        backdropFilter: 'blur(16px)',
      }}
    >
      {children}
    </div>
  );
};

export const DialogHeader: React.FC<DialogHeaderProps> = ({ children }) => {
  return (
    <div className="mb-4">
      {children}
    </div>
  );
};

export const DialogTitle: React.FC<DialogTitleProps> = ({ children }) => {
  return (
    <h2
      className="text-lg font-semibold"
      style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}
    >
      {children}
    </h2>
  );
};

export const DialogDescription: React.FC<DialogDescriptionProps> = ({ children }) => {
  return (
    <p
      className="text-sm mt-2"
      style={{ color: 'var(--text-secondary)' }}
    >
      {children}
    </p>
  );
};

export const DialogFooter: React.FC<DialogFooterProps> = ({ children }) => {
  return (
    <div className="flex justify-end space-x-2 mt-6">
      {children}
    </div>
  );
};
