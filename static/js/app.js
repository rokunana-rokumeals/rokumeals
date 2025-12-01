// MBG Knowledge Graph JavaScript Functions

class MBGApp {
    constructor() {
        this.baseURL = '';
        this.init();
    }
    
    init() {
        console.log('MBG Knowledge Graph App initialized');
        this.bindEvents();
    }
    
    bindEvents() {
        // Additional event bindings can be added here
        document.addEventListener('DOMContentLoaded', () => {
            this.loadStats();
        });
    }
    
    async loadStats() {
        try {
            const response = await fetch('/api/stats/');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.updateStatsDisplay(data.data);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
    
    updateStatsDisplay(stats) {
        // Update any dynamic stats displays
        console.log('Stats loaded:', stats);
    }
    
    // Utility function for API calls
    async apiCall(endpoint, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, finalOptions);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
    
    // Format numbers with commas
    formatNumber(num) {
        return num.toLocaleString();
    }
    
    // Debounce function for search
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the app
const mbgApp = new MBGApp();