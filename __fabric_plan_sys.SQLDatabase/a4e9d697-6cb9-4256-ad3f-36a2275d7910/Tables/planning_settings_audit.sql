CREATE TABLE [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[planning_settings_audit] (
    [id]            INT            IDENTITY (1, 1) NOT NULL,
    [entityId]      INT            NULL,
    [entityType]    INT            NOT NULL,
    [visualId]      INT            NOT NULL,
    [value]         NVARCHAR (MAX) NULL,
    [operationType] INT            CONSTRAINT [DF_6cb74b6b827715c7aee56a03aec] DEFAULT ((2)) NOT NULL,
    [measureGuid]   NVARCHAR (255) NULL,
    [updatedBy]     NVARCHAR (128) NOT NULL,
    [updatedByUPN]  NVARCHAR (320) NOT NULL,
    [updatedAt]     INT            NOT NULL,
    CONSTRAINT [PK_ac5a125faf87569831de66f874f] PRIMARY KEY CLUSTERED ([id] ASC)
);


GO

CREATE NONCLUSTERED INDEX [idx_planning_settings_audit_visualId]
    ON [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[planning_settings_audit]([visualId] ASC);


GO

