export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: {
    code: string;
    message: string;
  };
}

export interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface PaginatedResponse<T, M extends PaginationMeta = PaginationMeta> {
  success: boolean;
  data: T[];
  meta: M;
}
