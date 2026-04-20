import { useEffect, useState } from "react";
import { api } from "../../../services/api";
import type { SoftwareSupplyChainUiSettingsDto } from "../../../types/softwareSupplyChain";
import { openExternalUrl } from "../openExternalUrl";

export function GitHubWorkspace() {
  const [draftRepoUrl, setDraftRepoUrl] = useState("");
  const [currentRepoUrl, setCurrentRepoUrl] = useState("");
  const [savedRepoUrls, setSavedRepoUrls] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setStatusMessage("");

    api.getSoftwareSupplyChainUiSettings()
      .then((payload) => {
        if (!active) return;
        applySettings(payload);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  function applySettings(payload: SoftwareSupplyChainUiSettingsDto) {
    const nextCurrentRepoUrl = payload.current_repo_url || payload.repo_url || "";
    setDraftRepoUrl(nextCurrentRepoUrl);
    setCurrentRepoUrl(nextCurrentRepoUrl);
    setSavedRepoUrls(payload.saved_repo_urls || []);
  }

  async function saveSettings(nextCurrentRepoUrl: string, nextSavedRepoUrls: string[]) {
    const payload = await api.saveSoftwareSupplyChainUiSettings({
      repo_url: nextCurrentRepoUrl,
      current_repo_url: nextCurrentRepoUrl,
      saved_repo_urls: nextSavedRepoUrls,
    });
    applySettings(payload);
    return payload;
  }

  async function handleSave() {
    try {
      setSaving(true);
      setError("");
      setStatusMessage("");
      await saveSettings(draftRepoUrl, savedRepoUrls);
      setStatusMessage("GitHub link saved and promoted to the current active repository.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSetCurrent(repoUrl: string) {
    try {
      setSaving(true);
      setError("");
      setStatusMessage("");
      await saveSettings(repoUrl, savedRepoUrls);
      setStatusMessage("Current GitHub link switched. Later agent runs will stay grounded on this repository.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Switch failed");
    } finally {
      setSaving(false);
    }
  }

  function handleOpenCurrent() {
    if (!currentRepoUrl.trim()) return;
    openExternalUrl(currentRepoUrl.trim());
  }

  return (
    <section className="ssc-workspace-shell">
      <div className="ssc-workspace-grid">
        <div className="ssc-workspace-panel">
          <div className="ssc-workspace-head">
            <p className="ssc-workspace-eyebrow">GitHub Workspace</p>
            <h2>GitHub Links</h2>
            <p>Maintain the repository entry points for the supply-chain workflow here. Saving a link pushes it into the saved list and makes it the active repository.</p>
          </div>

          {loading ? <div className="ssc-inline-note">Loading the current GitHub link...</div> : null}
          {error ? <div className="ssc-inline-error">{error}</div> : null}
          {statusMessage ? <div className="ssc-inline-success">{statusMessage}</div> : null}

          <div className="ssc-workspace-current">
            <span className="ssc-current-label">Current Active Link</span>
            <strong>{currentRepoUrl || "Not set yet"}</strong>
            <p>This link becomes the default repository context for later supply-chain agent runs.</p>
          </div>

          <div className="ssc-field-block">
            <label htmlFor="ssc-repo-url">Repository URL</label>
            <input
              id="ssc-repo-url"
              type="url"
              value={draftRepoUrl}
              onChange={(event) => setDraftRepoUrl(event.target.value)}
              placeholder="https://github.com/owner/repo"
              disabled={loading || saving}
            />
          </div>

          <div className="ssc-workspace-actions">
            <button
              className="ssc-primary-action"
              type="button"
              onClick={handleSave}
              disabled={loading || saving || !draftRepoUrl.trim()}
            >
              {saving ? "Saving..." : "Save link"}
            </button>
            <button
              className="ssc-secondary-action"
              type="button"
              onClick={handleOpenCurrent}
              disabled={loading || saving || !currentRepoUrl.trim()}
            >
              Open current GitHub
            </button>
          </div>
        </div>

        <div className="ssc-workspace-panel ssc-saved-links-panel">
          <div className="ssc-workspace-head">
            <p className="ssc-workspace-eyebrow">Saved Links</p>
            <h2>Saved Repositories</h2>
            <p>Every saved GitHub repository stays here so you can quickly change the active context for later agent work.</p>
          </div>

          <div className="ssc-saved-links-list">
            {savedRepoUrls.length ? savedRepoUrls.map((repoUrl) => {
              const isCurrent = repoUrl === currentRepoUrl;
              return (
                <article key={repoUrl} className={`ssc-saved-link-card${isCurrent ? " current" : ""}`}>
                  <div className="ssc-saved-link-head">
                    <strong>{repoUrl}</strong>
                    {isCurrent ? <span className="ssc-current-pill">Current</span> : null}
                  </div>
                  <div className="ssc-saved-link-actions">
                    <button
                      className="ssc-secondary-action"
                      type="button"
                      onClick={() => handleSetCurrent(repoUrl)}
                      disabled={saving || isCurrent}
                    >
                      {isCurrent ? "Current link" : "Make current"}
                    </button>
                    <button
                      className="ssc-secondary-action"
                      type="button"
                      onClick={() => openExternalUrl(repoUrl)}
                      disabled={saving}
                    >
                      Open
                    </button>
                  </div>
                </article>
              );
            }) : (
              <div className="ssc-empty-state">
                <strong>No saved links yet</strong>
                <p>Add a GitHub repository on the left and it will appear here as a reusable repository context.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
