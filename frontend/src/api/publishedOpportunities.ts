import { apiClient } from './client';
import type {
  AnonymizeRequest,
  AnonymizedPreview,
  BoondOpportunityListResponse,
  PaginationParams,
  PublishedOpportunity,
  PublishedOpportunityListResponse,
  PublishRequest,
} from '../types';

const BASE_PATH = '/published-opportunities';

/**
 * Get Boond opportunities where current user is main manager.
 * Requires admin or commercial role.
 */
export async function getMyBoondOpportunities(): Promise<BoondOpportunityListResponse> {
  const response = await apiClient.get<BoondOpportunityListResponse>(
    `${BASE_PATH}/my-boond`
  );
  return response.data;
}

/**
 * Anonymize an opportunity using AI.
 * Returns a preview of the anonymized content.
 */
export async function anonymizeOpportunity(
  request: AnonymizeRequest
): Promise<AnonymizedPreview> {
  const response = await apiClient.post<AnonymizedPreview>(
    `${BASE_PATH}/anonymize`,
    request
  );
  return response.data;
}

/**
 * Publish an anonymized opportunity.
 */
export async function publishOpportunity(
  request: PublishRequest
): Promise<PublishedOpportunity> {
  const response = await apiClient.post<PublishedOpportunity>(
    `${BASE_PATH}/publish`,
    request
  );
  return response.data;
}

/**
 * List published opportunities.
 * Available to all authenticated users.
 */
export async function listPublishedOpportunities(
  params?: PaginationParams
): Promise<PublishedOpportunityListResponse> {
  const response = await apiClient.get<PublishedOpportunityListResponse>(
    BASE_PATH,
    { params }
  );
  return response.data;
}

/**
 * Get a published opportunity by ID.
 */
export async function getPublishedOpportunity(
  id: string
): Promise<PublishedOpportunity> {
  const response = await apiClient.get<PublishedOpportunity>(
    `${BASE_PATH}/${id}`
  );
  return response.data;
}

/**
 * Close a published opportunity.
 * Can only be closed by the publisher or an admin.
 */
export async function closeOpportunity(
  id: string
): Promise<PublishedOpportunity> {
  const response = await apiClient.patch<PublishedOpportunity>(
    `${BASE_PATH}/${id}/close`
  );
  return response.data;
}
