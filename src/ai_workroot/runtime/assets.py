"""Active Asset runtime services."""

from __future__ import annotations

import sqlite3
from pathlib import Path
import shutil

from ai_workroot.core.assets import Asset, AssetPublication, AssetSurface
from ai_workroot.storage.sqlite import record_index_invalidation


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
          publication_status, surface_id, current_path, content_hash, updatedAt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          asset_type=excluded.asset_type,
          title=excluded.title,
          lifecycle_status=excluded.lifecycle_status,
          publication_status=excluded.publication_status,
          surface_id=excluded.surface_id,
          updatedAt=excluded.updatedAt
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
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="assets",
        subject_type="asset",
        subject_id=asset_id,
        reason=f"asset-changed:{asset_id}",
    )
    conn.commit()
    return asset


def record_asset_publication(
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
    publication_status: str = "metadata-only",
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
    if not surface.allows(asset.asset_type):
        raise ValueError(f"surface {surface.surface_id!r} does not allow asset type {asset.asset_type!r}")
    asset.publication_status = publication_status
    asset.surface_id = surface.surface_id
    asset.current_path = target_path
    if asset.original_path is None:
        asset.original_path = target_path
    publication = AssetPublication(
        publication_id=f"pub_{asset.asset_id}",
        asset_id=asset.asset_id,
        workroot_id=asset.workroot_id,
        surface_id=surface.surface_id,
        target_path=target_path,
        publication_status=publication_status,
        published_by=published_by,
        git_policy=surface.git_policy,
    )
    _store_publication(conn, workroot_id=workroot_id, asset=asset, surface=surface, publication=publication)
    conn.commit()
    return publication


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
    return record_asset_publication(
        conn,
        workroot_id=workroot_id,
        asset_id=asset_id,
        surface_id=surface_id,
        surface_path=surface_path,
        surface_type=surface_type,
        target_path=target_path,
        published_by=published_by,
        allowed_asset_types=allowed_asset_types,
        git_policy=git_policy,
    )


def publish_asset_to_surface(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    asset_id: str,
    surface_id: str,
    surface_path: Path | str,
    surface_type: str,
    target_path: str,
    published_by: str,
    allowed_asset_types: tuple[str, ...],
    content: str | bytes | None = None,
    source_file: Path | str | None = None,
    git_policy: str = "tracked",
) -> AssetPublication:
    if content is None and source_file is None:
        raise ValueError("publish_asset_to_surface requires content or source_file")
    if content is not None and source_file is not None:
        raise ValueError("publish_asset_to_surface accepts content or source_file, not both")
    surface_root = Path(surface_path).expanduser().resolve()
    destination = _resolve_surface_target(surface_root, target_path)
    asset = _load_asset(conn, workroot_id, asset_id)
    surface = AssetSurface(
        surface_id=surface_id,
        workroot_id=workroot_id,
        path=str(surface_root),
        surface_type=surface_type,
        allowed_asset_types=allowed_asset_types,
        git_policy=git_policy,
        created_by=published_by,
    )
    publication = asset.publish(surface, target_path, published_by)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source_file is not None:
        source = Path(source_file).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"source file does not exist: {source}")
        shutil.copyfile(source, destination)
    elif isinstance(content, bytes):
        destination.write_bytes(content)
    else:
        destination.write_text(str(content), encoding="utf-8")
    _store_publication(conn, workroot_id=workroot_id, asset=asset, surface=surface, publication=publication)
    conn.commit()
    return publication


def _store_publication(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    asset: Asset,
    surface: AssetSurface,
    publication: AssetPublication,
) -> None:
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
        SET publication_status = ?, surface_id = ?, current_path = ?, lifecycle_status = ?, updatedAt = COALESCE(updatedAt, '')
        WHERE workroot_id = ? AND asset_id = ?
        """,
        (
            asset.publication_status,
            asset.surface_id,
            asset.current_path,
            asset.lifecycle_status,
            workroot_id,
            asset.asset_id,
        ),
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
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="asset-publications",
        subject_type="asset-publication",
        subject_id=asset.asset_id,
        reason=f"asset-publication-changed:{asset.asset_id}",
    )


def _resolve_surface_target(surface_root: Path, target_path: str) -> Path:
    if not target_path or Path(target_path).is_absolute():
        raise ValueError("target_path must be a relative path under the asset surface")
    destination = (surface_root / target_path).resolve()
    if destination != surface_root and surface_root not in destination.parents:
        raise ValueError("target_path escapes the asset surface")
    return destination


def mark_asset_missing(conn: sqlite3.Connection, *, workroot_id: str, asset_id: str, missing_since: str) -> Asset:
    asset = _load_asset(conn, workroot_id, asset_id)
    asset.mark_missing(missing_since)
    conn.execute(
        """
        UPDATE assets
        SET lifecycle_status = ?, updatedAt = ?
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
        updated_at=str(row[_column(row, "updatedAt", 9)] or "") or None,
    )


def _column(row: sqlite3.Row | tuple[object, ...], name: str, index: int) -> str | int:
    if isinstance(row, sqlite3.Row):
        return name
    return index
