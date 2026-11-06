// A test file that fails to load: it requires a module that does not exist.
const missing = require('./does-not-exist');

test('never runs', () => {
  missing();
});
