import {
  Run,
  BenchmarkMetric,
  Diagnosis,
  PatchApproval,
  RunReport,
  AuditEvent,
  ApprovalStatus,
  PersonaConfig,
  SandboxStep,
  EvidenceRecord,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080';

class ApiClient {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
    });

    if (!res.ok) {
      let errorMessage = `API Error ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        }
      } catch {
        // use default error message
      }
      throw new Error(errorMessage);
    }

    return res.json() as Promise<T>;
  }

  async getHealth(): Promise<{ status: string; service: string; mock_llm: boolean }> {
    return this.request('/health');
  }

  async listRuns(): Promise<Run[]> {
    return this.request('/api/runs');
  }

  async clearAllRuns(): Promise<{ message: string }> {
    return this.request('/api/runs', { method: 'DELETE' });
  }

  async getRun(runId: string): Promise<Run> {
    return this.request(`/api/runs/${runId}`);
  }

  async createRun(payload: {
    target_type: string;
    target_url: string;
    repo_path: string;
    personas?: PersonaConfig[];
    objectives?: Record<string, any>;
    workload_config?: Record<string, any>;
  }): Promise<Run> {
    return this.request('/api/runs', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getSandboxSteps(runId: string): Promise<SandboxStep[]> {
    return this.request(`/api/runs/${runId}/sandbox-steps`);
  }

  async getRunStatus(runId: string): Promise<{
    id: string;
    status: string;
    failure_reason?: string | null;
    updated_at: string;
  }> {
    return this.request(`/api/runs/${runId}/status`);
  }

  async getRunMetrics(runId: string): Promise<BenchmarkMetric[]> {
    return this.request(`/api/runs/${runId}/metrics`);
  }

  async getRunDiagnosis(runId: string): Promise<Diagnosis> {
    return this.request(`/api/runs/${runId}/diagnosis`);
  }

  async submitApproval(
    runId: string,
    payload: {
      patch_hash: string;
      decision: ApprovalStatus;
      reviewed_by?: string;
      decision_reason?: string;
    }
  ): Promise<PatchApproval> {
    return this.request(`/api/runs/${runId}/approval`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getRunReport(runId: string): Promise<RunReport> {
    return this.request(`/api/runs/${runId}/report`);
  }

  async getRunAudit(runId: string): Promise<AuditEvent[]> {
    return this.request(`/api/runs/${runId}/audit`);
  }

  async getRunEvidence(runId: string): Promise<EvidenceRecord[]> {
    return this.request(`/api/runs/${runId}/evidence`);
  }

  async getLLMConfig(): Promise<{
    active_model: string;
    fallback_model: string;
    mock_mode: boolean;
    has_groq_key: boolean;
    has_openai_key: boolean;
    has_anthropic_key: boolean;
    has_gemini_key: boolean;
    available_models: string[];
  }> {
    return this.request('/api/config/llm');
  }

  async updateLLMConfig(payload: {
    model?: string;
    fallback_model?: string;
    mock_mode?: boolean;
  }): Promise<any> {
    return this.request('/api/config/llm', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }
}

export const api = new ApiClient();
