/**
 * OntoRalph API Client Module
 *
 * Provides methods for interacting with the OntoRalph backend API.
 */

const API_BASE = '/api';

/**
 * Custom API Error class
 */
class ApiError extends Error {
    constructor(message, code, retryable = false, retryAfter = null) {
        super(message);
        this.name = 'ApiError';
        this.code = code;
        this.retryable = retryable;
        this.retryAfter = retryAfter;
    }
}

/**
 * Make an API request
 * @param {string} endpoint - API endpoint (e.g., '/health')
 * @param {object} options - Fetch options
 * @returns {Promise<any>} Response data
 * @throws {ApiError} On API error
 */
async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };

    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();

        if (!response.ok) {
            // Parse error response
            const errorDetail = data.detail;

            if (typeof errorDetail === 'object') {
                throw new ApiError(
                    errorDetail.message || 'An error occurred',
                    errorDetail.code || 'UNKNOWN_ERROR',
                    errorDetail.retryable || false,
                    errorDetail.retry_after || null
                );
            } else {
                throw new ApiError(
                    errorDetail || 'An error occurred',
                    'UNKNOWN_ERROR',
                    false
                );
            }
        }

        return data;
    } catch (error) {
        if (error instanceof ApiError) {
            throw error;
        }

        // Network error or other issue
        throw new ApiError(
            error.message || 'Network error',
            'NETWORK_ERROR',
            true
        );
    }
}

// ============================================
// Public API
// ============================================

const api = {
    /**
     * Check server health
     * @returns {Promise<{status: string, version: string}>}
     */
    async health() {
        return request('/health');
    },

    /**
     * Create a session (exchange API key for token)
     * @param {string} provider - Provider name ('claude', 'openai', 'mock')
     * @param {string} apiKey - API key
     * @returns {Promise<{session_token: string, provider: string, expires_at: string}>}
     */
    async createSession(provider, apiKey) {
        return request('/session', {
            method: 'POST',
            body: JSON.stringify({ provider, api_key: apiKey }),
        });
    },

    /**
     * Validate a single definition
     * @param {string} definition - The definition to validate
     * @param {string} term - The term being defined
     * @param {boolean} isIce - Whether this is an ICE class
     * @returns {Promise<{status: string, results: object[], passed_count: number, failed_count: number}>}
     */
    async validate(definition, term, isIce) {
        return request('/validate', {
            method: 'POST',
            body: JSON.stringify({
                definition,
                term,
                is_ice: isIce,
            }),
        });
    },

    /**
     * Validate multiple definitions for comparison
     * @param {object[]} definitions - Array of definition objects
     * @returns {Promise<{comparisons: object[]}>}
     */
    async validateBatch(definitions) {
        return request('/validate', {
            method: 'POST',
            body: JSON.stringify({ definitions }),
        });
    },

    /**
     * Run the Ralph Loop (blocking)
     * @param {object} params - Run parameters
     * @param {string} params.iri - Class IRI
     * @param {string} params.label - Class label
     * @param {string} params.parent_class - Parent class IRI
     * @param {string[]} [params.sibling_classes] - Sibling class IRIs
     * @param {boolean} params.is_ice - Whether this is an ICE class
     * @param {string} [params.current_definition] - Existing definition to improve
     * @param {string} params.provider - LLM provider
     * @param {string} params.api_key - API key
     * @param {number} [params.max_iterations] - Max iterations
     * @returns {Promise<object>} Run result
     */
    async run(params) {
        return request('/run', {
            method: 'POST',
            body: JSON.stringify(params),
        });
    },

    /**
     * Run the Ralph Loop with SSE streaming
     * @param {object} params - Run parameters
     * @param {function} onEvent - Callback for SSE events (eventType, data)
     * @returns {object} Controller with abort() method and result promise
     */
    runStream(params, onEvent) {
        let eventSource = null;
        let aborted = false;

        const controller = {
            abort: () => {
                aborted = true;
                if (eventSource) {
                    eventSource.close();
                }
            }
        };

        controller.promise = (async () => {
            // First create a session
            const session = await this.createSession(params.provider, params.api_key);

            // Build query string
            const queryParams = new URLSearchParams({
                token: session.session_token,
                iri: params.iri,
                label: params.label,
                parent_class: params.parent_class,
                is_ice: params.is_ice.toString(),
                max_iterations: (params.max_iterations || 5).toString(),
            });

            if (params.sibling_classes?.length) {
                queryParams.set('sibling_classes', params.sibling_classes.join(','));
            }

            if (params.current_definition) {
                queryParams.set('current_definition', params.current_definition);
            }

            const url = `${API_BASE}/run/stream?${queryParams}`;

            return new Promise((resolve, reject) => {
                if (aborted) {
                    reject(new ApiError('Request aborted', 'ABORTED', false));
                    return;
                }

                eventSource = new EventSource(url);

                // Event handlers for each event type
                const eventTypes = [
                    'iteration_start',
                    'generate',
                    'critique',
                    'refine',
                    'verify',
                    'iteration_end',
                    'complete',
                    'error'
                ];

                eventTypes.forEach(eventType => {
                    eventSource.addEventListener(eventType, (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            onEvent(eventType, data);

                            if (eventType === 'complete') {
                                eventSource.close();
                                resolve(data);
                            } else if (eventType === 'error') {
                                eventSource.close();
                                reject(new ApiError(
                                    data.message || 'Stream error',
                                    data.code || 'STREAM_ERROR',
                                    data.retryable || false,
                                    data.retry_after || null
                                ));
                            }
                        } catch (e) {
                            console.error('Failed to parse SSE event:', eventType, e);
                        }
                    });
                });

                // Handle connection errors
                eventSource.onerror = (event) => {
                    if (aborted) {
                        return;
                    }
                    eventSource.close();
                    reject(new ApiError('Connection lost', 'CONNECTION_ERROR', true));
                };
            });
        })();

        return controller;
    },

    /**
     * Create a batch job
     * @param {object} params - Batch parameters
     * @returns {Promise<{job_id: string, status: string, total_classes: number}>}
     */
    async createBatchJob(params) {
        return request('/batch', {
            method: 'POST',
            body: JSON.stringify(params),
        });
    },

    /**
     * Get batch job status
     * @param {string} jobId - Job ID
     * @returns {Promise<object>}
     */
    async getBatchStatus(jobId) {
        return request(`/batch/${jobId}`);
    },

    /**
     * Cancel a batch job
     * @param {string} jobId - Job ID
     * @returns {Promise<void>}
     */
    async cancelBatchJob(jobId) {
        return request(`/batch/${jobId}`, {
            method: 'DELETE',
        });
    },

    /**
     * Stream batch job progress via SSE
     * @param {string} jobId - Job ID
     * @param {string} provider - LLM provider
     * @param {string} apiKey - API key
     * @param {function} onEvent - Callback for SSE events (eventType, data)
     * @returns {object} Controller with abort() method and result promise
     */
    async streamBatchProgress(jobId, provider, apiKey, onEvent) {
        let eventSource = null;
        let aborted = false;

        const controller = {
            abort: () => {
                aborted = true;
                if (eventSource) {
                    eventSource.close();
                }
            }
        };

        controller.promise = (async () => {
            // Create a session for authentication
            const session = await this.createSession(provider, apiKey);

            const url = `${API_BASE}/batch/${jobId}/stream?token=${encodeURIComponent(session.session_token)}`;

            return new Promise((resolve, reject) => {
                if (aborted) {
                    reject(new ApiError('Request aborted', 'ABORTED', false));
                    return;
                }

                eventSource = new EventSource(url);

                // Event handlers for each event type
                const eventTypes = [
                    'status',
                    'progress',
                    'class_start',
                    'class_complete',
                    'class_error',
                    'job_complete',
                    'error'
                ];

                eventTypes.forEach(eventType => {
                    eventSource.addEventListener(eventType, (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            onEvent(eventType, data);

                            if (eventType === 'job_complete') {
                                eventSource.close();
                                resolve(data);
                            } else if (eventType === 'error') {
                                eventSource.close();
                                reject(new ApiError(
                                    data.message || 'Stream error',
                                    data.code || 'STREAM_ERROR',
                                    false
                                ));
                            }
                        } catch (e) {
                            console.error('Failed to parse batch SSE event:', eventType, e);
                        }
                    });
                });

                // Handle connection errors
                eventSource.onerror = () => {
                    if (aborted) {
                        return;
                    }
                    eventSource.close();
                    reject(new ApiError('Connection lost', 'CONNECTION_ERROR', true));
                };
            });
        })();

        return controller;
    },

    /**
     * Download batch results as ZIP
     * @param {string} jobId - Job ID
     * @returns {Promise<Blob>} ZIP file blob
     */
    async downloadBatchResults(jobId) {
        const url = `${API_BASE}/batch/${jobId}/download`;
        const response = await fetch(url);

        if (!response.ok) {
            const data = await response.json();
            throw new ApiError(
                data.detail?.message || data.detail || 'Download failed',
                data.detail?.code || 'DOWNLOAD_ERROR',
                false
            );
        }

        return response.blob();
    },
};

// Make api available globally
window.api = api;
window.ApiError = ApiError;
