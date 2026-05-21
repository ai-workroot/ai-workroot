"""Active Asset runtime services."""

from __future__ import annotations

import sqlite3

from ai_workroot.core.assets import Asset, AssetPublication, AssetSurface


def create_internal_asset(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    asset_id: str,
    asset_type: str,
    title: str,
    summary: str = "",
    lifecycle_status: str = "active",
    updated_at: str = "",
) -> Asset:
    asset = Asset(
        asset_id=asset_id,
        workroot_id=workroot_id,
        asset_type=asset_type,
        title=title,
        summary=summary,
        lifecycle_status=lifecycle_status,
        publication_status="internal",
        updated_at=updated_at,
    )
    conn.execute(
        """
        INSERT INTO assets (
          asset_id, workroot_id, asset_type, title, lifecycle_status,
          publication_status, surface_id, current_path, content_hash, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          asset_type=excluded.asset_type,
          title=excluded.title,
          lifecycle_status=excluded.lifecycle_status,
          publication_status=excluded.publication_status,
          surface_id=excluded.surface_id,
          updated_at=excluded.updated_at
        """,
        (
            asset.asset_id,
            asset.workroot_id,
            asset.asset_type,
            asset.title,
            asset.lifecycle_status,
            asset.publication_status,
            asset.surface_id,
            asset.current_path,
            asset.content_hash,
            asset.updated_at,
        ),
    )
    conn.commit()
    return asset


def publish_asset(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    asset_id: str,
    surface_id: str,
    surface_path: str,
    surface_type: str,
    target_path: str,
    published_by: str,
    allowed_asset_types: tuple[str, ...],
    git_policy: str = "tracked",
) -> AssetPublication:
    asset = _load_asset(conn, workroot_id, asset_id)
    surface = AssetSurface(
        surface_id=surface_id,
        workroot_id=workroot_id,
        path=surface_path,
        surface_type=surface_type,
        allowed_asset_types=allowed_asset_types,
        git_policy=git_policy,
        created_by=published_by,
    )
    publication = asset.publish(surface, target_path, published_by)
    conn.execute(
        """
        INSERT INTO asset_surfaces (surface_id, workroot_id, path, surface_type, git_policy)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(surface_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          path=excluded.path,
          surface_type=excluded.surface_type,
          git_policy=excluded.git_policy
        """,
        (surface.surface_id, workroot_id, surface.path, surface.surface_type, surface.git_policy),
    )
    conn.execute(
        """
        UPDATE assets
        SET publication_status = ?, surface_id = ?, current_path = ?, lifecycle_status = ?, updated_at = COALESCE(updated_at, '')
        WHERE workroot_id = ? AND asset_id = ?
        """,
        (asset.publication_status, asset.surface_id, asset.current_path, asset.lifecycle_status, workroot_id, asset_id),
    )
    conn.execute(
        """
        INSERT INTO asset_publications (
          publication_id, asset_id, workroot_id, surface_id, target_path, publication_status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(publication_id) DO UPDATE SET
          asset_id=excluded.asset_id,
          workroot_id=excluded.workroot_id,
          surface_id=excluded.surface_id,
          target_path=excluded.target_path,
          publication_status=excluded.publication_status
        """,
        (
            publication.publication_id,
            publication.asset_id,
            publication.workroot_id,
            publication.surface_id,
            publication.target_path,
            publication.publication_status,
        ),
    )
    conn.commit()
    return publication


def mark_asset_missing(conn: sqlite3.Connection, *, workroot_id: str, asset_id: str, missing_since: str) -> Asset:
    asset = _load_asset(conn, workroot_id, asset_id)
    asset.mark_missing(missing_since)
    conn.execute(
        """
        UPDATE assets
        SET lifecycle_status = ?, updated_at = ?
        WHERE workroot_id = ? AND asset_id = ?
        """,
        (asset.lifecycle_status, missing_since, workroot_id, asset_id),
    )
    conn.commit()
    asset.updated_at = missing_since
    return asset


def query_assets(conn: sqlite3.Connection, workroot_id: str, *, asset_type: str | None = None) -> list[Asset]:
    params: list[object] = [workroot_id]
    where = ["workroot_id = ?"]
    if asset_type is not None:
        where.append("asset_type = ?")
        params.append(asset_type)
    rows = conn.execute(
        f"""
        SELECT *
        FROM assets
        WHERE {" AND ".join(where)}
        ORDER BY asset_id ASC
        """,
        params,
    ).fetchall()
    return [_asset_from_row(row) for row in rows]


def _load_asset(conn: sqlite3.Connection, workroot_id: str, asset_id: str) -> Asset:
    row = conn.execute(
        """
        SELECT *
        FROM assets
        WHERE workroot_id = ? AND asset_id = ?
        LIMIT 1
        """,
        (workroot_id, asset_id),
    ).fetchone()
    if row is None:
        raise ValueError(f"asset does not exist for Workroot {workroot_id}: {asset_id}")
    return _asset_from_row(row)


def _asset_from_row(row: sqlite3.Row) -> Asset:
    return Asset(
        asset_id=str(row[_column(row, "asset_id", 0)]),
        workroot_id=str(row[_column(row, "workroot_id", 1)]),
        asset_type=str(row[_column(row, "asset_type", 2)] or ""),
        title=str(row[_column(row, "title", 3)] or ""),
        lifecycle_status=str(row[_column(row, "lifecycle_status", 4)] or "active"),
        publication_status=str(row[_column(row, "publication_status", 5)] or "internal"),
        surface_id=str(row[_column(row, "surface_id", 6)] or "") or None,
        current_path=str(row[_column(row, "current_path", 7)] or "") or None,
        content_hash=str(row[_column(row, "content_hash", 8)] or "") or None,
        updated_at=str(row[_column(row, "updated_at", 9)] or "") or None,
    )


def _column(row: sqlite3.Row | tuple[object, ...], name: str, index: int) -> str | int:
    if isinstance(row, sqlite3.Row):
        return name
    return index
