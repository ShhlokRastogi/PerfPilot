// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { StatusBadge } from './components/StatusBadge';
import { MetricCard } from './components/MetricCard';

describe('PerfPilot Frontend Components', () => {
  it('renders StatusBadge for awaiting_approval correctly', () => {
    render(<StatusBadge status="awaiting_approval" />);
    expect(screen.getByText(/Awaiting Human Approval/i)).toBeDefined();
  });

  it('renders StatusBadge for completed correctly', () => {
    render(<StatusBadge status="completed" />);
    expect(screen.getByText(/Completed/i)).toBeDefined();
  });

  it('renders MetricCard with baseline and candidate comparison', () => {
    render(
      <MetricCard
        label="p95 Latency"
        baseline={450}
        candidate={30}
        unit="ms"
        improvementPct={93.3}
      />
    );
    expect(screen.getByText(/p95 Latency/i)).toBeDefined();
    expect(screen.getByText(/30/i)).toBeDefined();
    expect(screen.getByText(/Baseline: 450ms/i)).toBeDefined();
    expect(screen.getByText(/93.3%/i)).toBeDefined();
  });
});
