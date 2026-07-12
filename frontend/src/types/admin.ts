import { WardType, BedStatus } from "../lib/api";

export interface AnalyticsSummary {
  alert_triggered_count: number;
  recommendation_generated_count: number;
  approved_count: number;
  rejected_count: number;
  expired_count: number;
  ai_acceptance_rate: number;
  median_response_time_seconds: number;
}

export interface WardConfiguration {
  id: number;
  name: string;
  type: WardType;
  capacity: number;
}

export interface BedConfiguration {
  id: number;
  bed_number: string;
  status: BedStatus;
  ward_id: number;
}
