/** Typed wrappers over every endpoint the app uses. */

import { api, request } from './client';
import type {
  Assignment,
  AuthResponse,
  CoachPublic,
  CoachRegisterPayload,
  CoachStats,
  CurrentAssignment,
  Drill,
  Leaderboard,
  LeaderboardScope,
  LeaderboardWindow,
  Me,
  ReviewQueue,
  Roster,
  RosterEntry,
  Streak,
  StudentRegisterPayload,
  Submission,
  SubmissionSource,
  UploadTarget,
  Week,
} from './types';

export const endpoints = {
  // ---------------------------------------------------------------- auth
  coaches: () => request<CoachPublic[]>('/public/coaches', { auth: false }),

  login: (email: string, password: string) =>
    api.post<AuthResponse>('/auth/login', { email, password }, false),

  registerStudent: (payload: StudentRegisterPayload) =>
    api.post<AuthResponse>('/auth/register/student', payload, false),

  registerCoach: (payload: CoachRegisterPayload) =>
    api.post<AuthResponse>('/auth/register/coach', payload, false),

  me: () => api.get<Me>('/auth/me'),

  // -------------------------------------------------------------- student
  streak: () => api.get<Streak>('/me/streak'),
  weeks: (limit = 12) => api.get<{ weeks: Week[] }>(`/me/weeks?limit=${limit}`),
  currentAssignment: () => api.get<CurrentAssignment>('/assignments/current'),
  mySubmissions: (limit = 50) => api.get<Submission[]>(`/submissions/mine?limit=${limit}`),

  uploadTarget: (body: { content_type: string; content_hash: string; content_length?: number }) =>
    api.post<UploadTarget>('/submissions/upload-url', body),

  createSubmission: (body: {
    video_key: string;
    content_hash: string;
    drill_id?: string | null;
    duration_sec?: number | null;
    file_size_bytes?: number | null;
    mime_type?: string | null;
    source?: SubmissionSource;
    reps_claimed?: number | null;
    student_note?: string | null;
  }) => api.post<Submission>('/submissions', body),

  // ---------------------------------------------------------------- coach
  reviewQueue: (limit = 50) => api.get<ReviewQueue>(`/submissions/queue?limit=${limit}`),

  review: (id: string, body: { decision: 'approved' | 'rejected'; rating?: number | null; feedback?: string | null }) =>
    api.patch<Submission>(`/submissions/${id}/review`, body),

  roster: () => api.get<Roster>('/coach/roster'),
  coachStats: () => api.get<CoachStats>('/coach/stats'),

  updateRoster: (
    studentId: string,
    body: { coach_id?: string; batch_name?: string; remove?: boolean },
  ) => api.patch<RosterEntry>(`/coach/roster/${studentId}`, body),

  // --------------------------------------------------------------- drills
  drills: () => api.get<Drill[]>('/drills'),

  createDrill: (body: {
    title: string;
    description?: string | null;
    instructions?: string | null;
    metric_type?: 'reps' | 'duration_sec';
    target_value?: number;
    difficulty?: 'beginner' | 'intermediate' | 'advanced';
  }) => api.post<Drill>('/drills', body),

  assignments: (limit = 12) => api.get<Assignment[]>(`/assignments?limit=${limit}`),

  assign: (body: {
    batch_name: string;
    week_start?: string | null;
    notes?: string | null;
    drills: { drill_id: string; required_count?: number }[];
  }) => api.post<Assignment>('/assignments', body),

  // ---------------------------------------------------------- leaderboard
  leaderboard: (scope: LeaderboardScope, window: LeaderboardWindow, batch?: string) => {
    const params = new URLSearchParams({ scope, window });
    if (batch) params.set('batch', batch);
    return api.get<Leaderboard>(`/leaderboard?${params.toString()}`);
  },
};

export const queryKeys = {
  me: ['me'] as const,
  coaches: ['coaches'] as const,
  streak: ['streak'] as const,
  weeks: ['weeks'] as const,
  assignment: ['assignment'] as const,
  submissions: ['submissions'] as const,
  queue: ['queue'] as const,
  roster: ['roster'] as const,
  stats: ['stats'] as const,
  drills: ['drills'] as const,
  assignments: ['assignments'] as const,
  leaderboard: (scope: string, window: string, batch?: string) =>
    ['leaderboard', scope, window, batch ?? ''] as const,
};
