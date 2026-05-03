import React, { useRef, useState, useCallback } from 'react';
import { Upload, ImagePlus, X } from 'lucide-react';

interface PhotoUploadProps {
  images: File[];
  setImages: (files: File[]) => void;
  maxImages?: number;
}

const PhotoUpload: React.FC<PhotoUploadProps> = ({ images, setImages, maxImages = 5 }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files) return;
    const newFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
    const combined = [...images, ...newFiles].slice(0, maxImages);
    setImages(combined);
  }, [images, setImages, maxImages]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const removeImage = (idx: number) => {
    setImages(images.filter((_, i) => i !== idx));
  };

  return (
    <div>
      <div
        className={`upload-zone ${isDragging ? 'drag-active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: 'none' }}
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="upload-icon">
          {images.length === 0 ? <Upload size={36} /> : <ImagePlus size={28} />}
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          {images.length === 0
            ? 'Drop shelf images here or click to upload'
            : `${images.length}/${maxImages} images selected`}
        </p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginTop: '4px' }}>
          JPG, PNG up to 10MB each
        </p>
      </div>

      {images.length > 0 && (
        <div className="upload-previews">
          {images.map((file, idx) => (
            <div key={idx} style={{ position: 'relative' }}>
              <img
                className="upload-preview-img"
                src={URL.createObjectURL(file)}
                alt={`Preview ${idx + 1}`}
              />
              <button
                onClick={(e) => { e.stopPropagation(); removeImage(idx); }}
                style={{
                  position: 'absolute',
                  top: -4,
                  right: -4,
                  width: 20,
                  height: 20,
                  borderRadius: '50%',
                  background: 'var(--danger)',
                  color: '#fff',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 0,
                }}
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PhotoUpload;
