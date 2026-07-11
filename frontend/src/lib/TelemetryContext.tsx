"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { 
  fetchWards, 
  fetchPatients, 
  fetchPendingRecommendations, 
  fetchActiveAlerts, 
  fetchPartnerHospitals,
  Ward, 
  Bed,
  BedStatus,
  Patient, 
  RecommendationDetail, 
  Alert, 
  PartnerHospital,
  API_BASE_URL
} from "./api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAuth } from "./AuthContext";

interface TelemetryContextType {
  wards: Ward[];
  setWards: React.Dispatch<React.SetStateAction<Ward[]>>;
  patients: Patient[];
  setPatients: React.Dispatch<React.SetStateAction<Patient[]>>;
  recommendations: RecommendationDetail[];
  setRecommendations: React.Dispatch<React.SetStateAction<RecommendationDetail[]>>;
  alerts: Alert[];
  setAlerts: React.Dispatch<React.SetStateAction<Alert[]>>;
  partnerHospitals: PartnerHospital[];
  setPartnerHospitals: React.Dispatch<React.SetStateAction<PartnerHospital[]>>;
  
  loading: boolean;
  error: string | null;
  setError: (err: string | null) => void;
  loadData: () => Promise<void>;
  
  wsConnected: boolean;
  
  // Time Travel states
  isHistorical: boolean;
  historicalTime: string | null;
  enterTimeTravel: (timestamp: string) => Promise<void>;
  exitTimeTravel: () => Promise<void>;
}

const TelemetryContext = createContext<TelemetryContextType | undefined>(undefined);

export function TelemetryProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [wards, setWards] = useState<Ward[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationDetail[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [partnerHospitals, setPartnerHospitals] = useState<PartnerHospital[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Time Travel State
  const [isHistorical, setIsHistorical] = useState(false);
  const [historicalTime, setHistoricalTime] = useState<string | null>(null);

  // Live REST Loader
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [wardsData, patientsData, recsData, alertsData, partnersData] = await Promise.all([
        fetchWards(),
        fetchPatients(),
        fetchPendingRecommendations(),
        fetchActiveAlerts(),
        fetchPartnerHospitals()
      ]);
      setWards(wardsData);
      setPatients(patientsData);
      setRecommendations(recsData);
      setAlerts(alertsData);
      setPartnerHospitals(partnersData);
    } catch (err: any) {
      setError(err.message || "Failed to retrieve telemetry data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user || isHistorical) return;
    loadData();
  }, [user, isHistorical]);

  // Live WebSockets updates: only active when NOT in historical mode
  let rawWsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
  if (rawWsUrl.endsWith("/")) {
    rawWsUrl = rawWsUrl.slice(0, -1);
  }
  const wsBaseUrl = rawWsUrl;
  const wsUrl = typeof window !== "undefined" && user && !isHistorical ? `${wsBaseUrl}/ws/dashboard` : "";
  const { connected: wsConnected } = useWebSocket(
    wsUrl,
    (payload: any) => {
      console.log(`WebSocket event stream received: ${payload.type}`, payload);

      if (payload.type === "PATIENT_ADMITTED") {
        const newPatient = payload.data;
        setPatients((prev) => [newPatient, ...prev.filter(p => p.id !== newPatient.id)]);
        if (payload.recommendation) {
          setRecommendations((prev) => [payload.recommendation, ...prev.filter(r => r.id !== payload.recommendation.id)]);
        }
        fetchWards().then(setWards);
      } 
      
      else if (payload.type === "PATIENT_UPDATED") {
        const updated = payload.data;
        setPatients((prev) => prev.map(p => p.id === updated.patient_id ? { ...p, ...updated } : p));
        if (payload.recommendation) {
          setRecommendations((prev) => [payload.recommendation, ...prev.filter(r => r.id !== payload.recommendation.id)]);
        }
        fetchWards().then(setWards);
      } 
      
      else if (payload.type === "RECOMMENDATION_ACTIONED") {
        const actionedId = payload.data.recommendation_id;
        setRecommendations((prev) => prev.filter(r => r.id !== actionedId));
        fetchWards().then(setWards);
        fetchPatients().then(setPatients);
      } 
      
      else if (payload.type === "ALERT_TRIGGERED") {
        setAlerts((prev) => {
          const incoming = payload.data as Alert[];
          const filtered = prev.filter(a => !incoming.find(i => i.id === a.id));
          return [...incoming, ...filtered];
        });
      } 
      
      else if (payload.type === "RECOMMENDATION_GENERATED" || payload.type === "SHADOW_RECOMMENDATION_GENERATED") {
        const newRec = payload.data as RecommendationDetail;
        setRecommendations((prev) => [newRec, ...prev.filter(r => r.id !== newRec.id)]);
      }
      
      else if (payload.type === "ALERT_ACKNOWLEDGED") {
        const ackId = payload.data.alert_id;
        setAlerts((prev) => prev.filter(a => a.id !== ackId));
      } 
      
      else if (payload.type === "BED_UPDATED") {
        const updatedBed = payload.data;
        setWards((prevWards) => 
          prevWards.map((w) => {
            if (w.id === updatedBed.ward_id) {
              const updatedBeds = w.beds?.map((b) => 
                b.id === updatedBed.bed_id 
                  ? { ...b, status: updatedBed.status, patient_id: updatedBed.patient_id, patient: updatedBed.patient } 
                  : b
              ) || [];
              return { ...w, beds: updatedBeds };
            }
            return w;
          })
        );
      }

      else if (payload.type === "DELTA_REHYDRATION") {
        const { alerts: deltaAlerts, recommendations: deltaRecs } = payload.data;
        if (deltaAlerts && deltaAlerts.length > 0) {
          setAlerts((prev) => {
            const filtered = prev.filter(a => !deltaAlerts.find((da: any) => da.id === a.id));
            return [...deltaAlerts, ...filtered];
          });
        }
        if (deltaRecs && deltaRecs.length > 0) {
          setRecommendations((prev) => {
            const filtered = prev.filter(r => !deltaRecs.find((dr: any) => dr.id === r.id));
            return [...deltaRecs, ...filtered];
          });
        }
        fetchWards().then(setWards);
        fetchPatients().then(setPatients);
      }
    }
  );

  // Time Travel Handlers
  const enterTimeTravel = async (timestamp: string) => {
    try {
      setLoading(true);
      setError(null);
      setIsHistorical(true);
      setHistoricalTime(timestamp);

      const response = await fetch(`${API_BASE_URL}/api/state/snapshot?timestamp=${encodeURIComponent(timestamp)}`, { credentials: 'include' });
      if (!response.ok) {
        throw new Error("Failed to load historical snapshot from server.");
      }
      const snapshot = await response.json();
      setWards(snapshot.wards);
      setPatients(snapshot.patients);
      setRecommendations(snapshot.recommendations);
      setAlerts(snapshot.alerts);
    } catch (err: any) {
      setError(err.message || "Failed to retrieve historical snapshot.");
    } finally {
      setLoading(false);
    }
  };

  const exitTimeTravel = async () => {
    setIsHistorical(false);
    setHistoricalTime(null);
    await loadData();
  };

  return (
    <TelemetryContext.Provider value={{
      wards, setWards,
      patients, setPatients,
      recommendations, setRecommendations,
      alerts, setAlerts,
      partnerHospitals, setPartnerHospitals,
      loading, error, setError, loadData,
      wsConnected,
      isHistorical, historicalTime, enterTimeTravel, exitTimeTravel
    }}>
      {children}
    </TelemetryContext.Provider>
  );
}

export function useTelemetry() {
  const context = useContext(TelemetryContext);
  if (!context) {
    throw new Error("useTelemetry must be used within a TelemetryProvider");
  }
  return context;
}
