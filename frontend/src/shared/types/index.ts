export type Role = 'SYSTEM_ADMIN' | 'AGENCY_MANAGER' | 'AGENCY_OPERATOR' | 'CLIENT_DIRECTOR';

export type PlatformType = 'youtube' | 'instagram' | 'facebook' | 'x' | 'naver_blog';

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  status: 'active' | 'inactive' | 'locked';
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  status: string;
}
