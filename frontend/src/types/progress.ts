/**
 * Types for the dual gamification system (Streak & Batch)
 */

export interface StreakInfo {
  current: number;
  last_test_date: string | null;
  earned_milestones: string[];
  next_milestone: number;
  next_milestone_name: string;
  progress_to_next: number;
}

export interface BatchInfo {
  current_batch: string;
  current_star: number;
  xp_points: number;
  stars_per_batch: number;
  xp_to_next_star: number;
  next_batch: string | null;
}

export interface ProgressResponse {
  streak: StreakInfo;
  batch: BatchInfo;
  newly_earned_milestone?: string | null;
  stars_changed?: boolean;
  batch_upgraded?: boolean;
}

export const MILESTONE_BADGES: Record<string, { name: string; color: string; icon: string }> = {
  'Bronze (7)': { name: 'Bronze', color: '#CD7F32', icon: '🥉' },
  'Silver (15)': { name: 'Silver', color: '#C0C0C0', icon: '🥈' },
  'Gold (30)': { name: 'Gold', color: '#FFD700', icon: '🥇' },
  'Platinum (45)': { name: 'Platinum', color: '#E5E4E2', icon: '💎' },
  'Diamond (100)': { name: 'Diamond', color: '#B9F2FF', icon: '💠' },
};

export const BATCH_COLORS: Record<string, { primary: string; secondary: string; icon: string }> = {
  Bronze: { primary: '#CD7F32', secondary: '#F4A460', icon: '🥉' },
  Silver: { primary: '#C0C0C0', secondary: '#E8E8E8', icon: '🥈' },
  Gold: { primary: '#FFD700', secondary: '#FFF8DC', icon: '🥇' },
  Platinum: { primary: '#E5E4E2', secondary: '#F5F5F5', icon: '💎' },
};
