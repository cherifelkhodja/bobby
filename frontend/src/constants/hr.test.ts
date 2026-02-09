/**
 * Tests for HR constants - ensures all constants are properly defined
 * and maintain expected structure for consuming components.
 */

import { describe, it, expect } from 'vitest';
import {
  CONTRACT_TYPES,
  SALARY_CONTRACT_TYPES,
  TJM_CONTRACT_TYPES,
  EMPLOYEE_CONTRACT_TYPES,
  FREELANCE_CONTRACT_TYPES,
  CONTRACT_TYPE_LABELS,
  REMOTE_POLICIES,
  REMOTE_LABELS,
  EXPERIENCE_LEVELS,
  EXPERIENCE_LABELS,
  JOB_POSTING_STATUS_BADGES,
  AVAILABILITY_OPTIONS,
  AVAILABILITY_FILTER_OPTIONS,
  ENGLISH_LEVELS,
  SORT_OPTIONS,
  DISPLAY_MODE_OPTIONS,
} from './hr';

describe('HR Constants', () => {
  describe('CONTRACT_TYPES', () => {
    it('has PERMANENT, TEMPORARY, FREELANCE', () => {
      const values = CONTRACT_TYPES.map((ct) => ct.value);
      expect(values).toContain('PERMANENT');
      expect(values).toContain('TEMPORARY');
      expect(values).toContain('FREELANCE');
    });

    it('has matching labels in CONTRACT_TYPE_LABELS', () => {
      for (const ct of CONTRACT_TYPES) {
        expect(CONTRACT_TYPE_LABELS[ct.value]).toBeDefined();
      }
    });
  });

  describe('salary/TJM contract types', () => {
    it('SALARY_CONTRACT_TYPES includes employee contracts', () => {
      expect(SALARY_CONTRACT_TYPES).toContain('PERMANENT');
      expect(SALARY_CONTRACT_TYPES).toContain('TEMPORARY');
      expect(SALARY_CONTRACT_TYPES).not.toContain('FREELANCE');
    });

    it('TJM_CONTRACT_TYPES includes freelance', () => {
      expect(TJM_CONTRACT_TYPES).toContain('FREELANCE');
      expect(TJM_CONTRACT_TYPES).not.toContain('PERMANENT');
    });
  });

  describe('public form contract type categories', () => {
    it('EMPLOYEE_CONTRACT_TYPES exists', () => {
      expect(EMPLOYEE_CONTRACT_TYPES.length).toBeGreaterThan(0);
    });

    it('FREELANCE_CONTRACT_TYPES exists', () => {
      expect(FREELANCE_CONTRACT_TYPES.length).toBeGreaterThan(0);
    });
  });

  describe('REMOTE_POLICIES', () => {
    it('has NONE, PARTIAL, FULL', () => {
      const values = REMOTE_POLICIES.map((rp) => rp.value);
      expect(values).toEqual(['NONE', 'PARTIAL', 'FULL']);
    });

    it('has matching REMOTE_LABELS', () => {
      for (const rp of REMOTE_POLICIES) {
        expect(REMOTE_LABELS[rp.value]).toBe(rp.label);
      }
    });
  });

  describe('EXPERIENCE_LEVELS', () => {
    it('has 4 levels ordered by seniority', () => {
      const values = EXPERIENCE_LEVELS.map((el) => el.value);
      expect(values).toEqual(['JUNIOR', 'INTERMEDIATE', 'SENIOR', 'EXPERT']);
    });

    it('has matching EXPERIENCE_LABELS', () => {
      for (const el of EXPERIENCE_LEVELS) {
        expect(EXPERIENCE_LABELS[el.value]).toBe(el.label);
      }
    });
  });

  describe('JOB_POSTING_STATUS_BADGES', () => {
    it('has draft, published, closed', () => {
      expect(JOB_POSTING_STATUS_BADGES.draft).toBeDefined();
      expect(JOB_POSTING_STATUS_BADGES.published).toBeDefined();
      expect(JOB_POSTING_STATUS_BADGES.closed).toBeDefined();
    });

    it('each badge has label and color', () => {
      for (const badge of Object.values(JOB_POSTING_STATUS_BADGES)) {
        expect(badge.label).toBeTruthy();
        expect(badge.color).toBeTruthy();
      }
    });
  });

  describe('AVAILABILITY_OPTIONS vs AVAILABILITY_FILTER_OPTIONS', () => {
    it('filter options has an empty "all" option', () => {
      expect(AVAILABILITY_FILTER_OPTIONS[0].value).toBe('');
    });

    it('form options does not have an empty option', () => {
      expect(AVAILABILITY_OPTIONS.every((opt) => opt.value !== '')).toBe(true);
    });

    it('both share the same non-empty values', () => {
      const formValues = AVAILABILITY_OPTIONS.map((o) => o.value);
      const filterValues = AVAILABILITY_FILTER_OPTIONS.filter((o) => o.value !== '').map((o) => o.value);
      expect(filterValues).toEqual(formValues);
    });
  });

  describe('ENGLISH_LEVELS', () => {
    it('has 5 levels with descriptions', () => {
      expect(ENGLISH_LEVELS).toHaveLength(5);
      for (const level of ENGLISH_LEVELS) {
        expect(level.value).toBeTruthy();
        expect(level.label).toBeTruthy();
        expect(level.description).toBeTruthy();
      }
    });
  });

  describe('SORT_OPTIONS', () => {
    it('has valid sort keys', () => {
      const values = SORT_OPTIONS.map((s) => s.value);
      expect(values).toContain('score');
      expect(values).toContain('date');
    });
  });

  describe('DISPLAY_MODE_OPTIONS', () => {
    it('has 4 modes', () => {
      expect(DISPLAY_MODE_OPTIONS).toHaveLength(4);
    });

    it('each mode has value, label, icon', () => {
      for (const mode of DISPLAY_MODE_OPTIONS) {
        expect(mode.value).toBeTruthy();
        expect(mode.label).toBeTruthy();
        expect(mode.icon).toBeDefined();
      }
    });
  });
});
