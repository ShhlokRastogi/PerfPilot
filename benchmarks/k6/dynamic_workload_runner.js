import http from 'k6/http';
import { check, sleep } from 'k6';

// Universal dynamic workload runner for any web or API target
export const options = {
  vus: parseInt(__ENV.VUS || '10'),
  duration: (__ENV.DURATION_SEC || '10') + 's',
  gracefulStop: '1s',
  thresholds: {
    http_req_failed: ['rate<0.15'], // error rate threshold
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

export default function () {
  const targetUrl = __ENV.TARGET_URL || 'http://127.0.0.1:3000';
  const customHeadersJson = __ENV.CUSTOM_HEADERS_JSON;
  
  let headers = {
    'User-Agent': 'PerfPilot-Dynamic-Runner/2.0',
    'Accept': 'application/json, text/html, */*'
  };

  if (customHeadersJson) {
    try {
      const parsed = JSON.parse(customHeadersJson);
      headers = Object.assign({}, headers, parsed);
    } catch (e) {
      // Ignore header parsing errors
    }
  }

  const res = http.get(targetUrl, {
    headers: headers,
    tags: { name: 'TargetWorkload' },
    timeout: '15s'
  });

  check(res, {
    'status is valid': (r) => r.status >= 200 && r.status < 400,
  });

  // Brief jitter to simulate realistic concurrent load
  sleep(0.02);
}
