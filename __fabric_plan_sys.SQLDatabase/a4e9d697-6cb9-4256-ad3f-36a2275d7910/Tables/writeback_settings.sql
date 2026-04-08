CREATE TABLE [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[writeback_settings] (
    [id]        INT            IDENTITY (1, 1) NOT NULL,
    [visualId]  INT            NOT NULL,
    [meta]      NVARCHAR (MAX) NOT NULL,
    [status]    INT            CONSTRAINT [DF_9f10efbc84449f82c18a246129c] DEFAULT ((10)) NOT NULL,
    [createdBy] NVARCHAR (128) NOT NULL,
    [updatedBy] NVARCHAR (128) NOT NULL,
    [createdAt] INT            NOT NULL,
    [updatedAt] INT            NOT NULL,
    CONSTRAINT [PK_f7667e00688b086e1292e6615a2] PRIMARY KEY CLUSTERED ([id] ASC),
    CONSTRAINT [FK_94e8f3168953c07cd61ff067f34] FOREIGN KEY ([visualId]) REFERENCES [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[visual] ([id])
);


GO

