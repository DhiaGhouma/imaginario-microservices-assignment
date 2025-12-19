import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { videoAPI } from '../api';

interface Video {
  id: number;
  title: string;
  description: string;
  duration: number;
  created_at: string;
}

interface VideoState {
  videos: Video[];
  loading: boolean;
  error: string | null;
}

const initialState: VideoState = {
  videos: [],
  loading: false,
  error: null,
};

export const fetchVideos = createAsyncThunk(
  'videos/fetchVideos',
  async (userId: number) => {
    const response = await videoAPI.listVideos(userId);
    return Array.isArray(response) ? response : response.videos || [];
  }
);

export const createVideo = createAsyncThunk(
  'videos/createVideo',
  async ({ data }: { userId: number; data: { title: string; description?: string; duration?: number } }) => {
    return await videoAPI.createVideo(data);
  }
);

export const updateVideo = createAsyncThunk(
  'videos/updateVideo',
  async ({ videoId, data }: { userId: number; videoId: number; data: Partial<Video> }) => {
    return await videoAPI.updateVideo(videoId, data);
  }
);

export const deleteVideo = createAsyncThunk(
  'videos/deleteVideo',
  async ({ videoId }: { userId: number; videoId: number }) => {
    await videoAPI.deleteVideo(videoId);
    return videoId;
  }
);

const videoSlice = createSlice({
  name: 'videos',
  initialState,
  reducers: {
    clearVideos: (state) => {
      state.videos = [];
      state.error = null;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchVideos.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchVideos.fulfilled, (state, action) => {
        state.loading = false;
        state.videos = action.payload;
      })
      .addCase(fetchVideos.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch videos';
        state.videos = [];
      })
      .addCase(createVideo.fulfilled, (state, action) => {
        state.videos.push(action.payload);
      })
      .addCase(updateVideo.fulfilled, (state, action) => {
        const index = state.videos.findIndex(v => v.id === action.payload.id);
        if (index !== -1) {
          state.videos[index] = action.payload;
        }
      })
      .addCase(deleteVideo.fulfilled, (state, action) => {
        state.videos = state.videos.filter(v => v.id !== action.payload);
      });
  },
});

export const { clearVideos } = videoSlice.actions;
export default videoSlice.reducer;