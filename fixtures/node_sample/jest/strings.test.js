test('trims whitespace', () => {
  expect('  a  '.trim()).toBe('a');
});
test('throws on purpose', () => {
  throw new Error('boom');
});
