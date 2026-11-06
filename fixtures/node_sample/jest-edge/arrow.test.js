// A test whose own name holds "›", the character jest uses to join describe levels.
describe('second', () => {
  test('a › b', () => {
    expect(1).toBe(2);
  });
  test('plain', () => {});
});
