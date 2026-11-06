// A test that takes just over a minute, so mocha prints the run time as "(1m)".
describe('slow', function () {
  it('waits 61 seconds', function (done) {
    this.timeout(70000);
    setTimeout(done, 61000);
  });
});
