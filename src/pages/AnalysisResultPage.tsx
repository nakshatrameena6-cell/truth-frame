import React, { useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAnalysis } from '../api/analyses';
import { mapAnalysisRecordToInvestigationReport } from '../lib/investigationMapper';
import { MOCK_SCENARIOS, MOCK_HISTORY_REPORTS } from '../lib/mockScenarios';
import { ScenarioId, InvestigationReport } from '../types/investigation';
import { AnalysisResult } from '../components/investigation/AnalysisResult';
import { LoadingState } from '../components/investigation/LoadingState';
import { ErrorState } from '../components/investigation/ErrorState';

export const AnalysisResultPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Check if this ID maps to one of our standard mock scenarios or cached reports
  const mockReport = useMemo<InvestigationReport | null>(() => {
    if (!id) return null;
    if (id in MOCK_SCENARIOS) {
      return MOCK_SCENARIOS[id as ScenarioId];
    }
    const found = MOCK_HISTORY_REPORTS.find((r) => r.id === id);
    if (found) return found;
    return null;
  }, [id]);

  // Query backend API if not directly resolved from mock scenarios
  const {
    data: apiRecord,
    isLoading: isApiLoading,
    isError: isApiError,
    refetch,
  } = useQuery({
    queryKey: ['analysis', id],
    queryFn: () => getAnalysis(id || ''),
    enabled: !mockReport && !!id,
    retry: false,
  });

  // 1. Loading state
  if (!mockReport && isApiLoading) {
    return <LoadingState message="Retrieving audio investigation dossier..." />;
  }

  // 2. Resolve final report
  let report: InvestigationReport | null = mockReport;
  if (!report && apiRecord) {
    report = mapAnalysisRecordToInvestigationReport(apiRecord);
  }

  // 3. Fallback scenario if ID was not found anywhere
  if (!report) {
    // If backend failed and no mock matches, show error state
    if (isApiError) {
      return (
        <div className="py-12">
          <ErrorState
            title="Analysis dossier unavailable"
            whatHappened="The requested investigation record could not be found."
            why="The case ID might be incorrect, or the recording session expired."
            whatToDoNext="Verify the case identifier or launch a new analysis."
            onRetry={() => refetch()}
          />
        </div>
      );
    }

    // Default to Scenario A for immediate inspection if random ID
    report = MOCK_SCENARIOS['scenario-a'];
  }

  return (
    <AnalysisResult
      report={report}
      onBack={() => navigate('/history')}
    />
  );
};
