export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  profile_image_url: string | null;
}

export interface LoginResponse {
  tokens: TokenResponse;
  user: UserResponse;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
}

export interface PasswordResetRequestBody {
  email: string;
}

export interface PasswordResetBody {
  token: string;
  new_password: string;
}

export interface InviteAcceptRequest {
  token: string;
  name: string;
  password: string;
}

export interface InviteVerifyResponse {
  email: string;
  role: string;
  organization_name: string;
  expires_at: string;
}
