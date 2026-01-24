/**
 * OntoRalph IndexedDB Storage Module
 *
 * Provides persistent storage for:
 * - API keys (encrypted in a real app, stored as-is here for local use)
 * - Settings (theme, provider, iterations)
 * - Custom prompts (for advanced mode)
 * - Run history
 */

const DB_NAME = 'ontoralph';
const DB_VERSION = 1;

// Store names
const STORES = {
    SETTINGS: 'settings',
    API_KEYS: 'apiKeys',
    PROMPTS: 'prompts',
    HISTORY: 'history'
};

/**
 * Initialize the IndexedDB database
 * @returns {Promise<IDBDatabase>}
 */
function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => {
            console.error('Failed to open database:', request.error);
            reject(request.error);
        };

        request.onsuccess = () => {
            resolve(request.result);
        };

        request.onupgradeneeded = (event) => {
            const db = event.target.result;

            // Settings store (key-value pairs)
            if (!db.objectStoreNames.contains(STORES.SETTINGS)) {
                db.createObjectStore(STORES.SETTINGS, { keyPath: 'key' });
            }

            // API keys store (provider -> key)
            if (!db.objectStoreNames.contains(STORES.API_KEYS)) {
                db.createObjectStore(STORES.API_KEYS, { keyPath: 'provider' });
            }

            // Custom prompts store
            if (!db.objectStoreNames.contains(STORES.PROMPTS)) {
                db.createObjectStore(STORES.PROMPTS, { keyPath: 'name' });
            }

            // History store (auto-incrementing id)
            if (!db.objectStoreNames.contains(STORES.HISTORY)) {
                const historyStore = db.createObjectStore(STORES.HISTORY, {
                    keyPath: 'id',
                    autoIncrement: true
                });
                historyStore.createIndex('timestamp', 'timestamp', { unique: false });
                historyStore.createIndex('term', 'term', { unique: false });
            }
        };
    });
}

/**
 * Get a value from a store
 * @param {string} storeName
 * @param {string} key
 * @returns {Promise<any>}
 */
async function getValue(storeName, key) {
    try {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.get(key);

            request.onsuccess = () => {
                resolve(request.result?.value ?? request.result);
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    } catch (error) {
        console.warn('Storage not available:', error);
        return null;
    }
}

/**
 * Set a value in a store
 * @param {string} storeName
 * @param {object} data - Must include the keyPath field
 * @returns {Promise<void>}
 */
async function setValue(storeName, data) {
    try {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.put(data);

            request.onsuccess = () => {
                resolve();
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    } catch (error) {
        console.warn('Storage not available:', error);
    }
}

/**
 * Delete a value from a store
 * @param {string} storeName
 * @param {string} key
 * @returns {Promise<void>}
 */
async function deleteValue(storeName, key) {
    try {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.delete(key);

            request.onsuccess = () => {
                resolve();
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    } catch (error) {
        console.warn('Storage not available:', error);
    }
}

/**
 * Get all values from a store
 * @param {string} storeName
 * @returns {Promise<any[]>}
 */
async function getAllValues(storeName) {
    try {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();

            request.onsuccess = () => {
                resolve(request.result);
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    } catch (error) {
        console.warn('Storage not available:', error);
        return [];
    }
}

/**
 * Clear a store
 * @param {string} storeName
 * @returns {Promise<void>}
 */
async function clearStore(storeName) {
    try {
        const db = await openDatabase();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(storeName, 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.clear();

            request.onsuccess = () => {
                resolve();
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    } catch (error) {
        console.warn('Storage not available:', error);
    }
}

// ============================================
// Public API
// ============================================

const storage = {
    /**
     * Get a setting value
     * @param {string} key - Setting key
     * @returns {Promise<any>} Setting value or null
     */
    async getSetting(key) {
        const result = await getValue(STORES.SETTINGS, key);
        return result?.value ?? null;
    },

    /**
     * Set a setting value
     * @param {string} key - Setting key
     * @param {any} value - Setting value
     * @returns {Promise<void>}
     */
    async setSetting(key, value) {
        await setValue(STORES.SETTINGS, { key, value });
    },

    /**
     * Get an API key
     * @param {string} provider - Provider name (anthropic, openai)
     * @returns {Promise<string|null>} API key or null
     */
    async getApiKey(provider) {
        const result = await getValue(STORES.API_KEYS, provider);
        return result?.key ?? null;
    },

    /**
     * Set an API key
     * @param {string} provider - Provider name
     * @param {string} key - API key
     * @returns {Promise<void>}
     */
    async setApiKey(provider, key) {
        await setValue(STORES.API_KEYS, { provider, key });
    },

    /**
     * Get a custom prompt
     * @param {string} name - Prompt name
     * @returns {Promise<string|null>} Prompt content or null
     */
    async getPrompt(name) {
        const result = await getValue(STORES.PROMPTS, name);
        return result?.content ?? null;
    },

    /**
     * Set a custom prompt
     * @param {string} name - Prompt name
     * @param {string} content - Prompt content
     * @returns {Promise<void>}
     */
    async setPrompt(name, content) {
        await setValue(STORES.PROMPTS, { name, content });
    },

    /**
     * Get all prompts
     * @returns {Promise<object[]>}
     */
    async getAllPrompts() {
        return getAllValues(STORES.PROMPTS);
    },

    /**
     * Add a history entry
     * @param {object} entry - History entry
     * @returns {Promise<void>}
     */
    async addHistoryEntry(entry) {
        const entryWithTimestamp = {
            ...entry,
            timestamp: Date.now()
        };
        await setValue(STORES.HISTORY, entryWithTimestamp);
    },

    /**
     * Get all history entries
     * @returns {Promise<object[]>}
     */
    async getHistory() {
        const entries = await getAllValues(STORES.HISTORY);
        // Sort by timestamp descending (newest first)
        return entries.sort((a, b) => b.timestamp - a.timestamp);
    },

    /**
     * Get a single history entry
     * @param {number} id - Entry ID
     * @returns {Promise<object|null>}
     */
    async getHistoryEntry(id) {
        return getValue(STORES.HISTORY, id);
    },

    /**
     * Delete a single history entry
     * @param {number} id - Entry ID
     * @returns {Promise<void>}
     */
    async deleteHistoryEntry(id) {
        await deleteValue(STORES.HISTORY, id);
    },

    /**
     * Clear all history
     * @returns {Promise<void>}
     */
    async clearHistory() {
        await clearStore(STORES.HISTORY);
    },

    /**
     * Export history as JSON
     * @returns {Promise<string>} JSON string of all history entries
     */
    async exportHistory() {
        const entries = await this.getHistory();
        return JSON.stringify({
            version: 1,
            exportedAt: new Date().toISOString(),
            entries: entries
        }, null, 2);
    },

    /**
     * Import history from JSON
     * @param {string} jsonString - JSON string from export
     * @returns {Promise<number>} Number of entries imported
     */
    async importHistory(jsonString) {
        const data = JSON.parse(jsonString);

        if (!data.entries || !Array.isArray(data.entries)) {
            throw new Error('Invalid history format: missing entries array');
        }

        let imported = 0;
        for (const entry of data.entries) {
            // Remove the old id so a new one is auto-generated
            const { id, ...entryWithoutId } = entry;
            await setValue(STORES.HISTORY, {
                ...entryWithoutId,
                timestamp: entry.timestamp || Date.now(),
                imported: true,
                originalId: id
            });
            imported++;
        }

        return imported;
    },

    /**
     * Get history count
     * @returns {Promise<number>}
     */
    async getHistoryCount() {
        const entries = await getAllValues(STORES.HISTORY);
        return entries.length;
    },

    /**
     * Clear all data (for "Forget Keys" feature)
     * @returns {Promise<void>}
     */
    async clearAllData() {
        await Promise.all([
            clearStore(STORES.SETTINGS),
            clearStore(STORES.API_KEYS),
            clearStore(STORES.PROMPTS),
            clearStore(STORES.HISTORY)
        ]);
    }
};

// Make storage available globally
window.storage = storage;
