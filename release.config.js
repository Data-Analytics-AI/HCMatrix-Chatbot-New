/* eslint-disable quotes */
module.exports = {
    branches: ["master", { name: "dev", prerelease: true }],
    plugins: [
      "@semantic-release/commit-analyzer",
      "@semantic-release/release-notes-generator",
      "@semantic-release/changelog",
      [
        "@semantic-release/exec",
        {
          verifyReleaseCmd: "mkdir -p ./artifacts && echo ${nextRelease.version} > ./artifacts/.VERSION",
        },
      ],
      "@semantic-release/npm",
      [
        "@semantic-release/github",
        {
          assets: "release/*.tgz",
        },
      ],
      [
        "@semantic-release/git",
        {
          assets: ["./artifacts/.VERSION", "package.json", "CHANGELOG.md"],
          message: "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}"
        },
      ],
    ],
    preset: "angular",
  };
  