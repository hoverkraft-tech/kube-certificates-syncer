import assert from "node:assert/strict";
import { test } from "node:test";
import { GenericContainer, Wait } from "testcontainers";

class SyncerContainer extends GenericContainer {
  async beforeContainerCreated() {
    // Keep the deployment's read-only root filesystem through the lifecycle hook.
    this.hostConfig.ReadonlyRootfs = true;
  }
}

test("the production image imports the application as non-root and writes to its certificate volume", async (t) => {
  assert.ok(process.env.TESTED_IMAGE_REF, "TESTED_IMAGE_REF is required");
  let container;
  t.after(async () => container?.stop());
  container = await new SyncerContainer(process.env.TESTED_IMAGE_REF)
    .withDroppedCapabilities("ALL")
    .withSecurityOpt("no-new-privileges")
    .withTmpFs({ "/certs": "uid=10001,gid=10001,mode=0700" })
    .withEntrypoint(["python"])
    .withCommand([
      "-I",
      "-c",
      `
import os
from pathlib import Path
import kube_certificates_syncer.main

assert os.getuid() == 10001
assert os.getgid() == 10001
assert os.statvfs("/").f_flag & os.ST_RDONLY
certificate = Path("/certs/smoke")
certificate.write_text("ok")
assert certificate.read_text() == "ok"
`,
    ])
    .withWaitStrategy(Wait.forOneShotStartup())
    .withStartupTimeout(30_000)
    .start();
});
