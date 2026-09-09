import { useState } from "react";
import "./UploadPanel.css";

function UploadPanel({
  onImageSelect,
  onProcess,
}) {
  const [imageType, setImageType] = useState("normal");

  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");

  const [demFile, setDemFile] = useState(null);
  const [imageFile, setImageFile] = useState(null);

  function handleImageChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setImageFile(file);
    onImageSelect(file);
  }

  function handleDemChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setDemFile(file);
  }

  function handleProcess() {
    if (!imageFile) {
      alert("Please select an RGB image first.");
      return;
    }

    if (imageType === "georeferenced") {
      if (!latitude || !longitude || !demFile) {
        alert(
          "Please enter Latitude, Longitude and select a DEM file."
        );
        return;
      }
    }

    onProcess({
      imageType,
      latitude,
      longitude,
      demFile,
    });
  }

  return (
    <div className="upload-panel">

      {/* =========================
          RGB IMAGE
      ========================= */}

      <div className="upload-field">
        <label className="field-label">
          RGB image
        </label>

        <label className="file-area">
          {imageFile ? (
            <div>
              <div className="file-selected">
                Image selected
              </div>

              <div className="file-name">
                {imageFile.name}
              </div>
            </div>
          ) : (
            <div>
              <div className="file-main">
                Choose an image
              </div>

              <div className="file-help">
                JPG, PNG, TIFF or GeoTIFF
              </div>
            </div>
          )}

          <span className="file-button">
            {imageFile ? "Change" : "Browse"}

            <input
              type="file"
              accept="image/*,.tif,.tiff"
              onChange={handleImageChange}
            />
          </span>
        </label>
      </div>

      {/* =========================
          IMAGE TYPE
      ========================= */}

      <div className="upload-field">
        <label className="field-label">
          Image type
        </label>

        <div className="type-options">

          {/* NORMAL */}

          <label>
            <input
              type="radio"
              name="imageType"
              checked={imageType === "normal"}
              onChange={() => {
                setImageType("normal");
              }}
            />

            <span>
              Normal RGB
            </span>
          </label>

          {/* GEOREFERENCED */}

          <label>
            <input
              type="radio"
              name="imageType"
              checked={imageType === "georeferenced"}
              onChange={() => {
                setImageType("georeferenced");
              }}
            />

            <span>
              Georeferenced RGB
            </span>
          </label>

        </div>
      </div>

      {/* =========================
          GEOREFERENCED INPUTS
      ========================= */}

      {imageType === "georeferenced" && (
        <div className="geo-fields">

          {/* LATITUDE */}

          <div className="upload-field">
            <label className="field-label">
              Latitude
            </label>

            <input
              className="text-input"
              type="number"
              step="any"
              placeholder="e.g. 13.6288"
              value={latitude}
              onChange={(event) =>
                setLatitude(event.target.value)
              }
            />
          </div>

          {/* LONGITUDE */}

          <div className="upload-field">
            <label className="field-label">
              Longitude
            </label>

            <input
              className="text-input"
              type="number"
              step="any"
              placeholder="e.g. 79.4192"
              value={longitude}
              onChange={(event) =>
                setLongitude(event.target.value)
              }
            />
          </div>

          {/* DEM */}

          <div className="upload-field">
            <label className="field-label">
              Reference DEM / SRTM
            </label>

            <label className="dem-button">
              {demFile ? "Change DEM" : "Choose DEM"}

              <input
                type="file"
                accept=".tif,.tiff"
                onChange={handleDemChange}
              />
            </label>

            {demFile && (
              <div className="dem-name">
                {demFile.name}
              </div>
            )}
          </div>

        </div>
      )}

      {/* =========================
          PROCESS
      ========================= */}

      <button
        className="process-button"
        onClick={handleProcess}
        disabled={!imageFile}
      >
        Process image
      </button>

    </div>
  );
}

export default UploadPanel;