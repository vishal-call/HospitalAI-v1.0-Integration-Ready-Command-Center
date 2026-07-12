import { useState, useEffect, useCallback, useRef } from "react";
import { 
  Ward, 
  Bed, 
  UserRole,
  fetchWards, 
  fetchBeds, 
  fetchAnalyticsSummary,
  createWard,
  deleteWard,
  createBed,
  deleteBed,
  updateStaffRole,
  WardCreatePayload,
  BedCreatePayload
} from "../lib/api";
import { AnalyticsSummary } from "../types/admin";

export function useAdminMetrics() {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [summaryMetrics, setSummaryMetrics] = useState<AnalyticsSummary | null>(null);
  const [wardsList, setWardsList] = useState<Ward[]>([]);
  const [bedsList, setBedsList] = useState<Bed[]>([]);

  const isFetchingRef = useRef<boolean>(false);

  // 1. Silent refresh of analytics summary (for background polling)
  const refreshAnalytics = useCallback(async (silent = false) => {
    if (isFetchingRef.current) return;
    if (!silent) setIsLoading(true);
    isFetchingRef.current = true;
    try {
      const data = await fetchAnalyticsSummary();
      setSummaryMetrics(data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to refresh admin analytics:", err);
      setError(err.message || "Failed to fetch analytics summary");
    } finally {
      isFetchingRef.current = false;
      if (!silent) setIsLoading(false);
    }
  }, []);

  // 2. Fetch list of wards and beds
  const refreshWardsAndBeds = useCallback(async () => {
    setIsLoading(true);
    try {
      const [wards, beds] = await Promise.all([
        fetchWards(),
        fetchBeds()
      ]);
      setWardsList(wards);
      setBedsList(beds);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch wards and beds:", err);
      setError(err.message || "Failed to fetch ward/bed configuration");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load
  const loadAllData = useCallback(async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        refreshAnalytics(true),
        refreshWardsAndBeds()
      ]);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load admin data");
    } finally {
      setIsLoading(false);
    }
  }, [refreshAnalytics, refreshWardsAndBeds]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Polling effect: every 30 seconds trigger silent analytics refresh
  useEffect(() => {
    const interval = setInterval(() => {
      refreshAnalytics(true);
    }, 30000);
    return () => clearInterval(interval);
  }, [refreshAnalytics]);

  // 3. Admin mutations
  const handleAddWard = async (payload: WardCreatePayload) => {
    setIsLoading(true);
    try {
      await createWard(payload);
      await refreshWardsAndBeds();
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to create ward");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveWard = async (id: number) => {
    setIsLoading(true);
    try {
      await deleteWard(id);
      await refreshWardsAndBeds();
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to delete ward");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddBed = async (payload: BedCreatePayload) => {
    setIsLoading(true);
    try {
      await createBed(payload);
      await refreshWardsAndBeds();
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to create bed");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveBed = async (id: number) => {
    setIsLoading(true);
    try {
      await deleteBed(id);
      await refreshWardsAndBeds();
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to delete bed");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateStaffRole = async (email: string, role: UserRole) => {
    setIsLoading(true);
    try {
      await updateStaffRole(email, role);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to update staff role");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isLoading,
    error,
    summaryMetrics,
    wardsList,
    bedsList,
    refreshAnalytics,
    refreshWardsAndBeds,
    loadAllData,
    handleAddWard,
    handleRemoveWard,
    handleAddBed,
    handleRemoveBed,
    handleUpdateStaffRole
  };
}
