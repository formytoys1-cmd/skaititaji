module.exports = {
  ci: {
    collect: {
      // URL задаётся через переменную окружения LHCI_URL в CI (live-сайт).
      url: [
        (process.env.LHCI_URL || 'https://skaititaji.onrender.com') + '/',
        (process.env.LHCI_URL || 'https://skaititaji.onrender.com') + '/login',
        (process.env.LHCI_URL || 'https://skaititaji.onrender.com') + '/palidziba',
      ],
      numberOfRuns: 1,
      settings: {
        // Мобильная эмуляция (по умолчанию у Lighthouse — mobile).
        preset: 'desktop',
        emulatedFormFactor: 'mobile',
      },
    },
    assert: {
      assertions: {
        // Пороги качества (0..1). Ниже — CI падает.
        'categories:accessibility': ['error', { minScore: 0.95 }],
        'categories:best-practices': ['warn', { minScore: 0.9 }],
        'categories:seo': ['warn', { minScore: 0.9 }],
        'categories:performance': ['warn', { minScore: 0.5 }],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
};
