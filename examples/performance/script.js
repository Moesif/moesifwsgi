import http from 'k6/http';
import { sleep, check } from 'k6';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

export const options = {
  vus: 20,
  duration: '1h',
};

export default function() {
  const endpoints = ['http://127.0.0.1:5050/todo/api/v1.0/tasks?n=150', 'http://127.0.0.1:5050/todo/api/v1.0/tasks?n=55', 'http://127.0.0.1:5050/todo/api/v1.0/tasks', 'http://127.0.0.1:5050/todo/api/v1.0/tasks?n=750'];
  const randomIndex = randomIntBetween(0, endpoints.length - 1);
  const randomEndpoint = endpoints[randomIndex];

  let res = http.get(randomEndpoint);
  check(res, { "status is 200 to 300": (res) => res.status < 400 });
  sleep(1);
}
