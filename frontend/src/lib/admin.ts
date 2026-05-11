import { api } from "@/lib/api";
import type { User } from "@/lib/auth";

export const usersKey = ["admin", "users"] as const;

export async function listUsers(): Promise<User[]> {
  const resp = await api.get<User[]>("/auth/users");
  return resp.data;
}

export async function activateUser(id: string): Promise<User> {
  const resp = await api.post<User>(`/auth/users/${id}/activate`, {});
  return resp.data;
}
