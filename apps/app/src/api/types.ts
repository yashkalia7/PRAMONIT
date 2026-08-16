/** Types mirroring the FastAPI schemas in apps/api/app/schemas. */

export type Role = 'coach' | 'student';
export type SubmissionStatus = 'pending' | 'approved' | 'rejected';
export type SubmissionSource = 'camera' | 'gallery' | 'web';
export type DominantFoot = 'left' | 'right' | 'both';
export type MetricType = 'reps' | 'duration_sec';
export type Difficulty = 'beginner' | 'intermediate' | 'advanced';
export type LeaderboardScope = 'batch' | 'coach' | 'academy';
export type LeaderboardWindow = 'week' | 'all';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface CoachPublic {
  id: string;
  full_name: string;
  specialization: string | null;
  primary_location: string | null;
  batches: string[];
  student_count: number;
}

export interface CoachProfile {
  bio: string | null;
  qualifications: string | null;
  years_experience: number | null;
  specialization: string | null;
  primary_location: string | null;
  batches: string[];
}

export interface StudentProfile {
  coach_id: string | null;
  coach_name: string | null;
  roster_status: 'active' | 'removed';
  batch_name: string | null;
  course: string | null;
  jersey_number: number | null;
  preferred_position: string | null;
  dominant_foot: DominantFoot | null;
  height_cm: number | null;
  weight_kg: number | null;
  years_playing: number | null;
  previous_club: string | null;
  school_name: string | null;
  guardian_name: string | null;
  guardian_phone: string | null;
  guardian_email: string | null;
  emergency_contact: string | null;
  medical_notes: string | null;
  address: string | null;
  joined_at: string | null;
  consent_media: boolean;
}

export interface Me {
  id: string;
  email: string;
  role: Role;
  full_name: string;
  phone: string | null;
  dob: string | null;
  avatar_url: string | null;
  coach_profile: CoachProfile | null;
  student_profile: StudentProfile | null;
}

export interface AuthResponse {
  tokens: TokenPair;
  user: Me;
}

export interface Drill {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  instructions: string | null;
  category: string;
  metric_type: MetricType;
  target_value: number;
  target_label: string;
  difficulty: Difficulty;
  demo_video_url: string | null;
  thumbnail_url: string | null;
  is_global: boolean;
}

export interface AssignmentItem {
  drill: Drill;
  required_count: number;
  sort_order: number;
}

export interface Assignment {
  id: string;
  coach_id: string;
  batch_name: string;
  week_start: string;
  week_label: string;
  notes: string | null;
  items: AssignmentItem[];
}

export interface CurrentAssignment {
  week_start: string;
  week_label: string;
  assignment: Assignment | null;
  fallback_drills: Drill[];
}

export interface UploadTarget {
  upload_url: string;
  method: string;
  video_key: string;
  headers: Record<string, string>;
  expires_in: number;
  max_bytes: number;
}

export interface Submission {
  id: string;
  student_id: string;
  student_name: string | null;
  batch_name: string | null;
  coach_id: string | null;
  drill: { id: string; title: string; target_label: string } | null;
  status: SubmissionStatus;
  source: SubmissionSource;
  duration_sec: number | null;
  reps_claimed: number | null;
  student_note: string | null;
  coach_rating: number | null;
  coach_feedback: string | null;
  auto_approved: boolean;
  reviewed_at: string | null;
  counts_for_week: string;
  week_label: string;
  submitted_at: string;
  playback_url: string | null;
}

export interface ReviewQueue {
  total_pending: number;
  oldest_waiting_hours: number | null;
  items: Submission[];
}

export interface Week {
  week_start: string;
  week_label: string;
  approved_count: number;
  pending_count: number;
  rejected_count: number;
  required_count: number;
  met: boolean;
  finalised: boolean;
  is_current: boolean;
}

export interface Streak {
  current_weeks: number;
  longest_weeks: number;
  last_met_week: string | null;
  provisional: boolean;
  total_approved: number;
  total_points: number;
  this_week: Week;
}

export interface LeaderboardRow {
  rank: number;
  student_id: string;
  full_name: string;
  batch_name: string | null;
  points: number;
  current_weeks: number;
  approved_total: number;
  is_viewer: boolean;
}

export interface Leaderboard {
  scope: LeaderboardScope;
  window: LeaderboardWindow;
  week_start: string | null;
  total_students: number;
  rows: LeaderboardRow[];
  viewer_row: LeaderboardRow | null;
}

export interface RosterEntry {
  student_id: string;
  full_name: string;
  email: string;
  batch_name: string | null;
  course: string | null;
  jersey_number: number | null;
  preferred_position: string | null;
  current_weeks: number;
  approved_total: number;
  points: number;
  this_week_approved: number;
  this_week_pending: number;
  required_count: number;
  at_risk: boolean;
  joined_at: string | null;
}

export interface Roster {
  batches: string[];
  students: RosterEntry[];
}

export interface BatchStat {
  batch_name: string;
  student_count: number;
  on_track: number;
  at_risk: number;
  compliance_pct: number;
}

export interface CoachStats {
  week_start: string;
  week_label: string;
  total_students: number;
  pending_reviews: number;
  oldest_waiting_hours: number | null;
  on_track: number;
  at_risk: number;
  compliance_pct: number;
  batches: BatchStat[];
}

export interface StudentRegisterPayload {
  email: string;
  password: string;
  full_name: string;
  coach_id: string;
  phone?: string | null;
  dob?: string | null;
  batch_name?: string | null;
  course?: string | null;
  jersey_number?: number | null;
  preferred_position?: string | null;
  dominant_foot?: DominantFoot | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  years_playing?: number | null;
  previous_club?: string | null;
  school_name?: string | null;
  guardian_name?: string | null;
  guardian_phone?: string | null;
  guardian_email?: string | null;
  emergency_contact?: string | null;
  medical_notes?: string | null;
  address?: string | null;
  consent_media?: boolean;
}

export interface CoachRegisterPayload {
  email: string;
  password: string;
  full_name: string;
  phone?: string | null;
  dob?: string | null;
  bio?: string | null;
  qualifications?: string | null;
  years_experience?: number | null;
  specialization?: string | null;
  primary_location?: string | null;
  batches?: string[];
}
