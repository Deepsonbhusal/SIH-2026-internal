function UploadPanel({ onImageSelect, onProcess }) {
  function handleImageChange(event) {
    const file = event.target.files[0];

    if (file) {
      onImageSelect(file);
    }
  }

  return (
    <div>
      <h2>Upload Satellite Image</h2>

      <input
        type="file"
        accept="image/*"
        onChange={handleImageChange}
      />

      <br />
      <br />

      <button onClick={onProcess}>
        Process Image
      </button>
    </div>
  );
}

export default UploadPanel;